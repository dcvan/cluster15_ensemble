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
from multiprocessing import Process, Manager, RLock, Queue, Value

from message_sender import MessageSender
from config import MESSAGE_BROKER_URI, CONDOR_EXE_DIR, TIMEOUT

class WorkflowMonitor(Process):
    '''
    Monitor workflow status
    
    '''
    def __init__(self, status, workdir):
        '''
        
        :param subprocess.Value status: whether the workflow is done
        :param str workdir: workflow working directory
        
        '''
        Process.__init__(self)
        self._status = status
        self._workdir = workdir
        self._cmd = ('pegasus-status -l %s' % workdir).split(' ')
        
    def run(self):
        '''
        Override
        
        '''
        while self._status.value == 1:
            while not os.path.isdir(self._workdir):
                time.sleep(5)
            p = subprocess.Popen(self._cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            if not err:
                for l in out.split('\n'):
                    if re.match('[ \t]+[0-9]+', l):
                        self._status.value = 1 if re.split('[ \t]+', l)[9] == 'Running' else 0
                        break 
            else:
                pass
            time.sleep(10)

class ProcessMonitor(object):
    '''
    A monitor to check a list of processes' system resource utilization
    
    '''
    def __init__(self, run_id, workflow, executables, workdir):
        '''
        Init

        :param str run_id: experiment ID
        :param str workflow: workflow type
        :param set executables: executables to be monitored
        :param str workdir: workflow working directory
        
        '''
        manager = Manager()
       
        
        self._run_id = run_id
        self._workflow = workflow
        self._msg_q = Queue()
        self._procs = set(executables)
        self._workdir = workdir
        self._hostname = socket.gethostname()
        self._status = Value('b', 1)
        self._status_monitor = WorkflowMonitor(self._status, self._workdir)
        self._sender = MessageSender(
                self._workflow, 
                self._run_id,
                pika.URLParameters(MESSAGE_BROKER_URI), 
                self._msg_q,
                self._hostname,
                )
        self._cur = None
        self._interval = 1
        self._timeout_counter = 0
        self._lock = RLock()
        self._stat = manager.dict({
                    'run_id': self._run_id,
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
        self._status_monitor.start()
        
        # start workflow monitor
        self._msg_q.put({
           'run_id': self._run_id,
           'workflow': self._workflow,
           'hostname': self._hostname,
           'timestamp': int(time.time() * 1000),
           'status': 'workflow_init'
        })
        while self._status.value == 1: # check workflow status
            while not self._cur:
                print('Waiting ...')
                # timeout
                if self._hostname != 'master' and self._timeout_counter >= TIMEOUT:
                    self._status.value = 0
                if self._status.value != 1:
                    break
                self._cur = self.find_process()
                time.sleep(self._interval)
                self._timeout_counter += 1
                
            if self._status.value == 1:
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
                            'run_id': self._run_id,
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
            
            if self._hostname == 'master':
                self._msg_q.put({
                    'run_id': self._run_id,
                    'hostname': self._hostname,
                    'timestamp': int(time.time() * 1000),
                    'status': 'workflow_finished',
                    'walltime': self._get_walltime(self._workdir)
                    })
            else:
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
            
if __name__ == '__main__':
    try:
        ProcessMonitor(
                str(uuid.uuid4()),
                'genomic-single', 
                set(['bwa', 'picard', 'gatk', 'samtools']),
                '/home/pegasus-user/genomics/wf_exon_irods/pegasus-user/pegasus/exonalignwf/run0001').run()
    except KeyboardInterrupt:
        pass
