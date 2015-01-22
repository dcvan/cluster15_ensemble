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
    def __init__(self, exp_id, msg_q):
        '''
        
        :param str exp_id: experiment ID
        :param subprocess.Queue msg_q: message queue for sending data to message sender
        
        '''
        Process.__init__(self)
        self._exp_id = exp_id
        self._msg_q = msg_q
        self._hostname = socket.gethostname()
        
    def run(self):
        '''
        Override
        
        '''
        while True:
            while not os.listdir(CONDOR_EXE_DIR):
                print('Waiting ...')
                time.sleep(5)
            self._msg_q.put({
                'exp_id': self._exp_id,
                'type': 'system',
                'host': self._hostname,
                'timestamp': time.time(),
                'sys_cpu_percent': psutil.cpu_percent(),
                'sys_mem_percent': psutil.virtual_memory().percent,
                'sys_read_bytes': psutil.disk_io_counters().read_bytes,
                'sys_write_bytes': psutil.disk_io_counters().write_bytes,
                'sys_net_bytes_sent': int(psutil.net_io_counters().bytes_sent),
                'sys_net_bytes_recv': int(psutil.net_io_counters().bytes_recv),
            })
            time.sleep(5)
        
    
class ProcessMonitor(object):
    '''
    A monitor to check a list of processes' system resource utilization
    
    '''
    def __init__(self, exp_id, executables, interval=1, workdir_base=None, run_num=0):
        '''
        Init

        :param str exp_id: experiment ID
        :param set executables: executables to be monitored
        :param str workdirs: workflow working directories
        
        '''
        manager = Manager()
        
        self._exp_id = exp_id
        self._msg_q = Queue()
        self._procs = set(executables)
        self._interval = interval
        self._workdir_base = workdir_base
        self._run_num = run_num
        self._hostname = socket.gethostname()
        self._sender = MessageSender(
                self._exp_id,
                pika.URLParameters(MESSAGE_BROKER_URI), 
                self._msg_q,
                self._hostname,
                )
        if self._workdir_base:
            self._done = Value('i', 0)
            self._status_monitor = WorkflowMonitor(self._done, self._workdir_base, self._run_num)
        self._is_worker = True if not self._workdir_base else self._find_startd()
        if self._is_worker:
            self._system_monitor = SystemMonitor(self._exp_id, self._msg_q)
        self._cur = None
        self._lock = RLock()
        self._stat = manager.dict({
                    'exp_id': self._exp_id,
                    'host': self._hostname,
                    'start_time': 0,
                    'type': 'process',
                    'terminate_time': 0,
                    'timestamp': 0,
                    'count':0,
                    'cmdline': None,
                    'runtime': 0.0,
                    'min_cpu_percent': 0.0,
                    'max_cpu_percent': 2000.0,
                    'avg_cpu_percent': 0.0,
                    'min_mem_percent': 0.0,
                    'max_mem_percent': 2000.0,
                    'avg_mem_percent': 0.0,
                    'total_read_bytes': 0,
                    'total_write_bytes': 0,
                    'status': None,
                    })
    
    def on_terminate(self, proc):
        '''
        Send a summary message when a process is terminated
        
        :param psutil.Process proc: the process just terminated
        
        '''
        with self._lock:
            if not self._stat['cmdline']: 
                return
            self._stat['status'] = 'terminated'
            self._stat['terminate_time'] = time.time()
            self._stat['runtime'] = self._stat['terminate_time'] - proc.create_time()
            if self._stat['count'] > 1:
                self._stat['avg_cpu_percent'] /= self._stat['count'] - 1
                self._stat['avg_mem_percent'] /= self._stat['count']
            else:
                self._stat['avg_cpu_percent'] = 0
                self._stat['avg_mem_percent'] = 0
            self._stat['timestamp'] = time.time()
            self._msg_q.put(dict(self._stat))
            print(self._stat)

    def find_process(self):
        '''
        Find any running process of interest. Because only an interesting job will be running at 
        any point of time, it simply returns the first found process of interest
        
        :rtype - psutil.Process
        
        '''
        if not os.listdir(CONDOR_EXE_DIR):
            return None
        proc = psutil.Process(int(os.listdir(CONDOR_EXE_DIR)[0][4:]))
        try:
            children = proc.children(recursive=True)
            for p in children:
                executable = None                
                if p.name() == 'python':
                    executable = p.cmdline()[1].split('/')[-1]
                elif p.name() == 'java':
                    executable = p.parent().cmdline()[1].split('/')[-1]
                else:
                    executable = p.name()
                if executable and executable in self._procs:
                    if p.name() == 'python':
                        self._stat['cmdline'] = ' '.join([arg.split('/')[-1] for arg in p.cmdline() if arg != 'python'])
                    elif p.name() == 'java':
                        self._stat['cmdline'] = ' '.join([arg.split('/')[-1] for arg in p.parent().cmdline() if arg != 'bash'])
                    else:
                        self._stat['cmdline'] = ' '.join([arg.split('/')[-1] for arg in p.cmdline()])
                    wait = Process(target=psutil.wait_procs, args=([p], None, self.on_terminate))
                    wait.start()
                    return p
        except psutil.NoSuchProcess:
            return None

    def run(self):
        '''
        Start the monitor. It creates an AMQP sender and sends job statistics periodically
         
        '''
        self._sender.start()
        if self._workdir_base:
            # master-specific config
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
                    print('Waiting ...')
                    if (self._workdir_base and self._done.value >= self._run_num):
                        break;
                    self._cur = self.find_process()
                    if self._cur: break
                    time.sleep(self._interval)
                if self._workdir_base and self._done.value >= self._run_num:
                    break;
                with self._lock:
                    try:
                        if not self._stat['status']:
                            self._stat['status'] = 'started'
                            self._stat['start_time'] = self._cur.create_time()
                        else:
                            self._stat['status'] = 'running'
                        self._stat['count'] += 1
                        cpu_percent = self._cur.cpu_percent(interval=self._interval)
                        if cpu_percent:
                            self._stat['max_cpu_percent'] = max(self._stat['max_cpu_percent'], cpu_percent)
                            self._stat['min_cpu_percent'] = min(self._stat['min_cpu_percent'], cpu_percent)
                        self._stat['avg_cpu_percent'] += cpu_percent
                        if mem_percent:
                            self._stat['max_mem_percent'] = max(self._stat['max_mem_percent'], self._cur.memory_percent())
                            self._stat['min_mem_percent'] = min(self._stat['min_mem_percent'], self._cur.memory_percent())
                        self._stat['avg_mem_percent'] += self._cur.memory_percent()
                        self._stat['total_read_bytes'] = self._cur.io_counters().read_bytes
                        self._stat['total_write_bytes'] = self._cur.io_counters().write_bytes
                            
                        print(self._cur.pid, self._stat['cmdline'], cpu_percent, self._cur.memory_percent(), self._cur.io_counters())
                        self._msg_q.put({
                            'exp_id': self._exp_id,
                            'host': self._hostname,
                            'type': 'process',
                            'timestamp': time.time(),
                            'cmdline': self._stat['cmdline'],
                            'cpu_percent': cpu_percent,
                            'memory_percent': self._cur.memory_percent(),
                            'start_time': self._stat['start_time'],
                            'total_read_bytes': self._stat['total_read_bytes'],
                            'total_write_bytes': self._stat['total_write_bytes'],
                            'status': self._stat['status'],
                        })
                    except psutil.NoSuchProcess:
                        self._cur = None
                        with self._lock:
                            self._stat['count'] = 0
                            self._stat['cmdline'] = None
                            self._stat['runtime'] = 0.0
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
                            self._stat['timestamp'] = 0
                            self._stat['status'] = None
                #time.sleep(self._interval)
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
                        'status': 'finished',
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
        
    def _find_startd(self):
        '''
        Find if the host has condor_startd. If it has, it is a worker
        
        :rtype bool
        
        '''
        for p in psutil.process_iter():
            if p.name() == 'condor_startd':
                return True
        return False
    
if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--id', dest='exp_id', type=str, help='Experiment ID', required=True)
        parser.add_argument('-w', '--workdir-base', dest='workdir_base', type=str, help='Workflow working directory base')
        parser.add_argument('-n', '--int', dest='interval', type=int, help='Check-in interval for ProcessMonitor')
        parser.add_argument('-r', '--run-num', dest='run_num', type=int, help='Number of planned runs')
        parser.add_argument('-l', '--exec-list', nargs='+', type=str, dest='executables', help='Executables to be monitored')
        args = parser.parse_args()
        
        ProcessMonitor(
                args.exp_id,
                args.executables,
                args.interval if args.interval else 1,
                args.workdir_base,
                args.run_num
            ).run()
    except KeyboardInterrupt:
        pass
