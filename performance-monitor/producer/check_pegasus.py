#!/usr/bin/env python

import psutil
import time
import uuid
import pika
import socket
import subprocess
import os
import re
import shutil
from multiprocessing import Process, Manager, RLock, Queue, Array, Value

from message_sender import MessageSender
from config import MESSAGE_BROKER_URI, CONDOR_EXE_DIR, TIMEOUT

class WorkflowMonitor(Process):
    '''
    Monitor workflow status
    
    '''
    def __init__(self, done, status, workdirs):
        '''
        
        :param subprocess.Value done: number of done workflows
        :param subprocess.Array status: whether the workflow is done
        :param str workdirs: workflow working directories
        
        '''
        Process.__init__(self)
        self._status = status
        self._workdirs = workdirs
        self._cmd = (('pegasus-status -l %s' % self._workdirs[i]).split(' ') for i in range(0, len(self._workdirs)))
        self._done = done
        
    def run(self):
        '''
        Override
        
        '''
        while self._done.value < len(self._workdirs):
            for i in range(0, len(self._workdirs)):
                if os.path.isdir(self._workdir[i]):
                    p = subprocess.Popen(self._cmd[i], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out, err = p.communicate()
                if not err:
                    for l in out.split('\n'):
                        if re.match('[ \t]+[0-9]+', l):
                            if re.split('[ \t]+', l)[9] == 'Running':
                                self._status[i] = 1
                            else:
                                self._status[i] = 0
                                self._done.value += 1
                            break
                else:
                    pass
                time.sleep(10)
                             
class ProcessMonitor(object):
    '''
    A monitor to check a list of processes' system resource utilization
    
    '''
    def __init__(self, exp_id, workflow, executables, workdirs=None):
        '''
        Init

        :param str exp_id: experiment ID
        :param str workflow: workflow type
        :param set executables: executables to be monitored
        :param str workdirs: workflow working directories
        
        '''
        manager = Manager()
       
        
        self._exp_id = self._exp_id
        self._workflow = workflow
        self._msg_q = Queue()
        self._procs = set(executables)
        self._workdirs = workdirs
        self._hostname = socket.gethostname()
        self._sender = MessageSender(
                self._workflow, 
                self._exp_id,
                pika.URLParameters(MESSAGE_BROKER_URI), 
                self._msg_q,
                self._hostname,
                )
        if self._workdirs:
            self._status = Array('b', [1] * len(self._workdirs))
            self._done = Value('i', 0)
            self._status_monitor = WorkflowMonitor(self._status, self._done, self._workdirs)
        self._is_worker = False if not self._workdirs else self._find_startd()
        self._cur = None
        self._interval = 1
        if self._is_worker:
            self._timeout_counter = 0
        self._lock = RLock()
        self._stat = manager.dict({
                    'exp_id': self._exp_id,
                    'host': self._hostname,
                    'start_time': 0,
                    'terminate_time': 0,
                    'timestamp': 0,
                    'count':0,
                    'cmdline': None,
                    'runtime': 0.0,
                    'avg_cpu_percent': 0.0,
                    'avg_mem_percent': 0.0,
                    'total_read_count': 0,
                    'total_write_count': 0,
                    'total_read_bytes': 0,
                    'total_write_bytes': 0,
                    'read_rate': 0,
                    'write_rate': 0,
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
            self._stat['terminate_time'] = int(time.time() * 1000)
            self._stat['runtime'] = time.time() - proc.create_time()
            if self._stat['count'] > 1:
                self._stat['avg_cpu_percent'] /= self._stat['count'] - 1
                self._stat['avg_mem_percent'] /= self._stat['count']
            else:
                self._stat['avg_cpu_percent'] = 0
                self._stat['avg_mem_percent'] = 0
            self._stat['timestamp'] = int(time.time() * 1000)
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
                executable = None               # timeout 
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
            
        self._msg_q.put({
           'exp_id': self._exp_id,
           'workflow': self._workflow,
           'hostname': self._hostname,
           'timestamp': int(time.time() * 1000),
           'status': 'workflow_init'
        })
        
        if self._hostname == 'master':
            # master-specific config
            self._status_monitor.start()
            pass

        if self._is_worker:
            while True:
                while not self._cur: 
                    print('Waiting ...')
                    if (self._workdirs and self._done >= len(self._workdirs)):
                        break;
                    if self._timeout_counter:
                        if self._timeout_counter >= TIMEOUT:
                            break
                        self._timeout_counter += 1
                    time.sleep(self._interval)
                if self._workdirs and self._done >= len(self._workdirs):
                    break;
                if self._timeout_counter:
                    if self._timeout_counter >= TIMEOUT:
                        break
                    self._timeout_counter = 0
                with self._lock:
                    try:
                        if not self._stat['status']:
                            self._stat['status'] = 'started'
                            self._stat['start_time'] = int(time.time() * 1000)
                        else:
                            self._stat['status'] = 'running'
                        self._stat['count'] += 1
                        cpu_percent = self._cur.cpu_percent()
                        self._stat['avg_cpu_percent'] += cpu_percent
                        self._stat['avg_mem_percent'] += self._cur.memory_percent()
                        self._stat['total_read_count'] = self._cur.io_counters().read_count
                        self._stat['total_write_count'] = self._cur.io_counters().write_count
                        self._stat['total_read_bytes'] = self._cur.io_counters().read_bytes
                        self._stat['total_write_bytes'] = self._cur.io_counters().write_bytes
                            
                        print(self._cur.pid, self._stat['cmdline'], cpu_percent, self._cur.memory_percent(), self._cur.io_counters())
                        self._msg_q.put({
                            'exp_id': self._exp_id,
                            'host': self._hostname,
                            'timestamp': int(time.time() * 1000),
                            'cmdline': self._stat['cmdline'],
                            'cpu_percent': cpu_percent,
                            'memory_percent': self._cur.memory_percent(),
                            'start_time': self._stat['start_time'],
                            'total_read_count': self._stat['total_read_count'],
                            'total_write_count': self._stat['total_write_count'],
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
                            self._stat['avg_cpu_percent']= 0.0
                            self._stat['avg_mem_percent'] = 0.0
                            self._stat['total_read_count'] = 0
                            self._stat['total_write_count'] = 0
                            self._stat['total_read_bytes'] = 0
                            self._stat['total_write_bytes'] = 0
                            self._stat['timestamp'] = 0
                            self._stat['status'] = None
                time.sleep(self._interval)
                  
            if self._workdirs: 
                for w in self._workdirs:
                    self._msg_q.put({
                        'exp_id': self._exp_id,
                        'run_id': int(w[-2] if w[-1] == '/' else w[-1]),
                        'hostname': self._hostname,
                        'timestamp': int(time.time() * 1000),
                        'status': 'workflow_finished',
                        'walltime': self._get_walltime(w)
                    })
            self._msg_q.put(None)
                
            
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
                        if walltime_text:
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
        ProcessMonitor(
                str(uuid.uuid4()),
                'genomic-single', 
                set(['bwa', 'picard', 'gatk', 'samtools']),
                ['/home/pegasus-user/genomics/wf_exon_irods/pegasus-user/pegasus/exonalignwf/run0001']).run()
    except KeyboardInterrupt:
        pass
