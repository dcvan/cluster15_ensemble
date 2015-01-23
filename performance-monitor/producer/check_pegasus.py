#!/usr/bin/env python

import psutil
import time
import pika
import socket
import subprocess
import os
import re
import shutil
import argparse
from multiprocessing import Process, Manager, RLock, Queue, Value

from message_sender import MessageSender
from config import MESSAGE_BROKER_URI, CONDOR_EXE_DIR

class WorkflowMonitor(Process):
    '''
    Monitor workflow status
    
    '''
    def __init__(self, done, workdir_base, run_num):
        '''
        
        :param subprocess.Value done: number of done workflows
        :param str workdirs: workflow working directories
        
        '''
        Process.__init__(self)
        self._workdir_base = workdir_base
        self._run_num = run_num
        self._done = done
        self._finished = set({})
        
    def run(self):
        '''
        Override
        
        '''
        while self._done.value < self._run_num:
            if os.path.isdir(self._workdir_base):
                workdirs = os.listdir(self._workdir_base)
                for w in workdirs:
                    if w in self._finished: continue
                    d = '%s%s' % (self._workdir_base, w) if self._workdir_base[-1] == '/' else '%s/%s' % (self._workdir_base, w)
                    if os.path.isdir(d):
                        out, err = subprocess.Popen(('pegasus-status -l %s' % d).split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
                        if not err:
                            for l in out.split('\n'):
                                if re.match('[ \t]+[0-9]+', l):
                                    if re.split('[ \t]+', l)[9] != 'Running':
                                        self._finished.add(w)
                                        self._done.value += 1
                                    break
            time.sleep(10)
                             
class SystemMonitor(Process):
    '''
    System resource usage monitor
    
    '''
    def __init__(self, exp_id, hostname, msg_q):
        '''
        
        :param str exp_id: experiment ID
        :param str hostname: hostname
        :param subprocess.Queue msg_q: message queue for sending data to message sender
        
        '''
        Process.__init__(self)
        self._msg_q = msg_q
        self._count = Value('i', 0)
        self._start_time = Value('d', 0.0)
        self._lock = RLock()
        self._init_read_bytes = psutil.disk_io_counters().read_bytes
        self._init_write_bytes  = psutil.disk_io_counters().write_bytes
        self._init_bytes_sent = int(psutil.net_io_counters().bytes_sent)
        self._init_bytes_recv = int(psutil.net_io_counters().bytes_recv)
        self._stat = Manager().dict({
                'exp_id': exp_id,
                'host': hostname, 
                'type': 'system',
                'sys_cpu_percent':0,
                'sys_mem_percent':0,
                'sys_read_bytes':0,
                'sys_write_bytes':0,
                'sys_net_bytes_sent': 0,
                'sys_net_bytes_recv': 0,
                'sys_max_cpu_percent': 0,
                'sys_min_cpu_percent': 2000,
                'sys_max_mem_percent':0,
                'sys_min_mem_percent': 2000,
            })
        
    def run(self):
        '''
        Override
        
        '''
        self._start_time.value = time.time()
        while True:
            while not os.listdir(CONDOR_EXE_DIR):
                time.sleep(5)
            with self._lock:
                self._count.value += 1
                cpu_pct = psutil.cpu_percent()
                mem_pct = psutil.virtual_memory().percent
                self._stat['sys_cpu_percent'] = self._stat['sys_cpu_percent'] + cpu_pct if 'sys_cpu_percent' in self._stat else cpu_pct
                self._stat['sys_max_cpu_percent'] = max(self._stat['sys_max_cpu_percent'], cpu_pct)
                self._stat['sys_min_cpu_percent'] = min(self._stat['sys_min_cpu_percent'], cpu_pct)
                self._stat['sys_mem_percent'] = self._stat['sys_mem_percent'] + mem_pct if 'sys_mem_percent' in self._stat else mem_pct
                self._stat['sys_max_mem_percent'] = max(self._stat['sys_max_mem_percent'], mem_pct)
                self._stat['sys_min_mem_percent'] = min(self._stat['sys_min_mem_percent'], mem_pct)
                self._stat['sys_read_bytes'] = psutil.disk_io_counters().read_bytes - self._init_read_bytes
                self._stat['sys_write_bytes'] = psutil.disk_io_counters().write_bytes - self._init_write_bytes
                self._stat['sys_net_bytes_sent'] = int(psutil.net_io_counters().bytes_sent) - self._init_bytes_sent
                self._stat['sys_net_bytes_recv'] = int(psutil.net_io_counters().bytes_recv) - self._init_bytes_recv
            time.sleep(5)
        
    def send_statistics(self):
        '''
        Send system statistics at this point of time
        
        '''
        runtime = time.time() - self._start_time.value
        with self._lock:
            msg = dict(self._stat)
            msg['sys_cpu_percent'] /= self._count.value
            msg['sys_mem_percent'] /= self._count.value
            msg['sys_read_rate'] = self._stat['sys_read_bytes'] / runtime
            msg['sys_write_rate'] = self._stat['sys_write_bytes'] / runtime
            msg['sys_send_rate'] = self._stat['sys_net_bytes_sent'] / runtime
            msg['sys_recv_rate'] = self._stat['sys_net_bytes_recv'] / runtime
            msg['timestamp'] = time.time()
            self._msg_q.put(msg)
    
class ProcessMonitor(object):
    '''
    A monitor to check a list of processes' system resource utilization
    
    '''
    def __init__(self, exp_id, is_master=False, is_worker=False , run_num=0, workdir_base=None, executables=None):
        '''
        Init

        :param str exp_id: experiment ID
        :param set executables: executables to be monitored
        :param str workdirs: workflow working directories
        
        '''
        manager = Manager()
        
        # required fields
        self._exp_id = exp_id
        self._hostname = socket.gethostname()
        self._is_master = is_master
        self._is_worker = is_worker
        self._msg_q = Queue()
        self._cur = None
        self._lock = RLock()
        self._count = Value('i', 0)
        self._wait_processes = set()
        self._stat = manager.dict({
                    'exp_id': self._exp_id,
                    'host': self._hostname,
                    'type': 'job',
                    'max_cpu_percent': 0,
                    'min_cpu_percent': 2000,
                    'max_mem_percent': 0,
                    'min_mem_percent': 2000,
                    'avg_cpu_percent': 0,
                    'avg_mem_percent': 0,
                    'runtime': 0,
                    })
       
        self._sender = MessageSender(
                self._exp_id,
                pika.URLParameters(MESSAGE_BROKER_URI), 
                self._msg_q,
                self._hostname,
                )

        if self._is_master:
            self._workdir_base = workdir_base
            self._run_num = run_num
            self._done = Value('i', 0)
            self._status_monitor = WorkflowMonitor(self._done, self._workdir_base, self._run_num)
            
        if self._is_worker:
            self._system_monitor = SystemMonitor(self._exp_id, self._hostname,  self._msg_q)
            self._procs = set(executables)


    def on_terminate(self, proc):
        '''
        Send a summary message when a process is terminated
        
        :param psutil.Process proc: the process just terminated
        
        '''
        with self._lock:
            if not self._stat['cmdline']:
                return
            self._stat['timestamp'] = time.time()
            self._stat['runtime'] = self._stat['timestamp'] - proc.create_time() 
            if self._count.value > 1:
                self._stat['avg_cpu_percent'] /= self._count.value - 1
                self._stat['avg_mem_percent'] /= self._count.value
            else:
                self._stat['avg_cpu_percent'] = 0
                self._stat['avg_mem_percent'] = 0
            self._msg_q.put(dict(self._stat))
            self._count.value = 0
            self._stat['cmdline'] = None
            self._stat['runtime'] = 0
            self._stat['start_time'] = 0
            self._stat['terminate_time'] = 0
            self._stat['min_cpu_percent'] = 2000.0
            self._stat['max_cpu_percent'] = 0.0
            self._stat['avg_cpu_percent']= 0.0
            self._stat['min_mem_percent'] = 2000.0
            self._stat['max_mem_percent'] = 0.0 
            self._stat['avg_mem_percent'] = 0.0
            self._stat['total_read_bytes'] = 0
            self._stat['total_write_bytes'] = 0
            self._system_monitor.send_statistics()
            


    def find_process(self):
        '''
        Find any running process of interest. Because only an interesting job will be running at 
        any point of time, it simply returns the first found process of interest
        
        :rtype - psutil.Process
        
        '''
        pid = self._get_job_pid()
        if not pid: 
            return None
        with self._lock: 
            self._stat['pid'] = pid
        proc = psutil.Process(self._stat['pid'])
        if pid not in self._wait_processes:
            wait = Process(target=psutil.wait_procs, args=([proc], None, self.on_terminate))
            wait.start()
            self._wait_processes.add(pid)
        try:
            children = proc.children(recursive=True)
            for p in children:
                executable = None                
                if p.name() == 'python':
                    executable = p.cmdline()[1].split('/')[-1] if len(p.cmdline()) > 1 else None
                elif p.name() == 'java':
                    executable = p.parent().cmdline()[1].split('/')[-1] if len(p.parent().cmdline()) > 1 else None
                else:
                    executable = p.name()
                if executable and executable in self._procs:
                    with self._lock:
                        if p.name() == 'python':
                            self._stat['cmdline'] = ' '.join([arg.split('/')[-1] for arg in p.cmdline()[1:3]])
                        elif p.name() == 'java':
                            self._stat['cmdline'] = ' '.join([arg.split('/')[-1] for arg in p.parent().cmdline()[1:3]])
                        else:
                            self._stat['cmdline'] = ' '.join([arg.split('/')[-1] for arg in p.cmdline()[:2]])
                    return p
        except psutil.NoSuchProcess:
            return None

    def run(self):
        '''
        Start the monitor. It creates an AMQP sender and sends job statistics periodically
         
        '''
        self._sender.start()
        if self._is_master:
            self._status_monitor.start()

        if self._is_worker:
            self._system_monitor.start()
            self._msg_q.put({
                    'exp_id': self._exp_id,
                    'type': 'worker',
                    'host': self._hostname,
                    'timestamp': int(time.time()),
                })
            while True:
                while not self._cur: 
                    if self._is_master and self._done.value >= self._run_num:
                        break;
                    self._cur = self.find_process()
                    if self._cur: 
                        break
                    time.sleep(1)
                if self._is_master and self._done.value >= self._run_num:
                    break;
                with self._lock:
                    try:
                        cpu_percent = self._cur.cpu_percent()
                        mem_percent = self._cur.memory_percent()
                        self._stat['max_cpu_percent'] = max(self._stat['max_cpu_percent'], cpu_percent)
                        if cpu_percent:
                            self._stat['min_cpu_percent'] = min(self._stat['min_cpu_percent'], cpu_percent)
                        self._stat['avg_cpu_percent'] += cpu_percent
                        self._stat['max_mem_percent'] = max(self._stat['max_mem_percent'], mem_percent)
                        self._stat['min_mem_percent'] = min(self._stat['min_mem_percent'], mem_percent)
                        self._stat['avg_mem_percent'] += mem_percent
                        
                        self._stat['total_read_bytes'] = self._cur.io_counters().read_bytes
                        self._stat['total_write_bytes'] = self._cur.io_counters().write_bytes
                        self._count.value += 1
                    except psutil.NoSuchProcess:
                        self._cur = None
                        self._count.value = 0
                time.sleep(1)
        else:
            while self._done.value < self._run_num:
                time.sleep(10)
                  
        if self._workdir_base: 
            if os.path.isdir(self._workdir_base):
                for w in os.listdir(self._workdir_base):
                    d = '%s%s' % (self._workdir_base, w) if self._workdir_base[-1] == '/' else '%s/%s' % (self._workdir_base, w)
                    self._msg_q.put({
                        'exp_id': self._exp_id,
                        'run_id': int(d[-1]),
                        'type': 'run',
                        'timestamp': time.time(),
                        'walltime': self._get_walltime(d)
                    })
            
    def _get_walltime(self, workdir):
        '''
        Get workflow wall time
        
        :param str workdir: workflow working directory
        :rtype int
        
        '''
        if os.path.isdir('%s/statistics' % workdir):
            shutil.rmtree('%s/statistics' % workdir)
        p = subprocess.Popen(['pegasus-statistics', workdir], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if not err:
            for l in out.split('\n'):
                if len(l) > 1 and l[0] != '#':
                    l = l.lower()
                    if 'workflow wall time' in l:
                        walltime_text = l.split(':')[1].strip()
                        if walltime_text and walltime_text != '-':
                            fs = walltime_text.split(',')
                            return int(fs[0].split(' ')[0]) * 60 + int(fs[1].split(' ')[1])
        else:
            # pegasus-statistics error
            # can be pre-mature workflow run or working directory does not exist
            return None
        
    def _get_job_pid(self):
        '''
        '''
        return int(os.listdir(CONDOR_EXE_DIR)[0][4:]) if os.listdir(CONDOR_EXE_DIR) else None
        
if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--id', dest='exp_id', type=str, help='Experiment ID', required=True)
        parser.add_argument('-m', '--master', dest='is_master', default=False, action='store_true', help='Master')
        parser.add_argument('-w', '--worker', dest='is_worker', default=False, action='store_true', help='Worker')
        parser.add_argument('-d', '--dir', dest='workdir_base', type=str, help='Workflow working directory base')
        parser.add_argument('-r', '--run-num', dest='run_num', type=int, help='Number of planned runs')
        parser.add_argument('-l', '--exec-list', nargs='+', type=str, dest='executables', help='Executables to be monitored')
        args = parser.parse_args()
        
        ProcessMonitor(
                args.exp_id,
                args.is_master,
                args.is_worker,
                args.run_num,
                args.workdir_base,
                args.executables,
            ).run()
    except KeyboardInterrupt:
        pass
