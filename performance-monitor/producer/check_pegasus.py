#!/usr/bin/env python

import psutil
import time
import pika
import socket
from multiprocessing import Process, Manager, RLock, Queue

from message_sender import MessageSender
from config import MESSAGE_BROKER_URI, TIMEOUT

class ProcessMonitor(object):
    '''
    A monitor to check a list of processes' system resource utilization
    
    '''
    def __init__(self, name, msg_q, executables):
        '''
        Init
        
        :param str name: workflow name(montage or genomic)
        :param multiprocessing.Queue msg_q: system message queue for communication between the monitor and AMQP sender
        :param set executables: executables to be monitored
        
        '''
        manager = Manager()
        self._msg_q = msg_q
        self._procs = list(executables)
        self._hostname = 'condor-0' if socket.gethostname() == 'master' else socket.gethostname()
        self._name = name
        self._expid = int(time.time() * 1000)
        self._sender = MessageSender(
                self._name, 
                self._expid,
                pika.URLParameters(MESSAGE_BROKER_URI), 
                self._msg_q,
                self._hostname,
                )
        self._cur = None
        self._interval = 1
        self._timeout_counter = 0
        self._step = manager.Value('i', 0)
        self._lock = RLock()
        self._stat = manager.dict({
                    'host': self._hostname,
                    'expid': self._expid,
                    'name': self._name, 
                    'timestamp': 0,
                    'count':0,
                    'step': 0,
                    'executable': None,
                    'runtime': 0.0,
                    'avg_cpu_percent': 0.0,
                    'avg_mem_percent': 0.0,
                    'total_read_count': 0,
                    'total_write_count': 0,
                    'total_read_bytes': 0,
                    'total_write_bytes': 0,
                    'read_rate': 0,
                    'write_rate': 0,
                    'status': 'terminated',
                    })
    
    def on_terminate(self, proc):
        '''
        Send a summary message when a process is terminated
        
        :param psutil.Process proc: the process just terminated
        
        '''
        if self._stat['count'] > 1:
            with self._lock:
                self._step.set(self._step.get() + 1) 
                self._stat['step'] = self._step.get()
                self._stat['runtime'] = time.time() - proc.create_time()
                self._stat['avg_cpu_percent'] /= self._stat['count'] - 1
                self._stat['avg_mem_percent'] /= self._stat['count']
                self._stat['read_rate'] = self._stat['total_read_bytes' ]/self._stat['runtime']
                self._stat['write_rate'] = self._stat['total_write_bytes' ]/self._stat['runtime']
                self._stat['timestamp'] = int(time.time() * 1000)
                self._msg_q.put(dict(self._stat))
                print(self._stat)

    def find_process(self):
        '''
        Find any running process of interest. Because only an interesting job will be running at 
        any point of time, it simply returns the first found process of interest
        
        :rtype - psutil.Process
        
        '''
        if self._procs: # always true except no executable is passed in
            for proc in psutil.process_iter():
                try:
                    if proc.name() == 'condor_starter':
                        self._stat['step'] = self._step.get()
                        children = proc.children(recursive=True)
                        for p in children:
                            if p.name() in self._procs:
                                wait = Process(target=psutil.wait_procs, args=([p], None, self.on_terminate))
                                wait.start()
                                return p
                except psutil.NoSuchProcess:
                    pass

    def run(self):
        '''
        Start the monitor. It creates an AMQP sender and sends job statistics periodically
         
        '''
        self._sender.start()
        while self._procs: # always true except no executable is passed in
            while not self._cur:
                # timeout 
                if self._timeout_counter >= TIMEOUT:
                    self._msg_q.put('stopping')
                print('Waiting ...')
                self._cur = self.find_process()
                time.sleep(1)
                self._timeout_counter += 1
            self._timeout_counter = 0
            with self._lock:
                try:
                    self._stat['count'] += 1
                    if not self._stat['executable']:
                        if self._cur.name() == 'python':
                            self._stat['executable'] = self._cur.cmdline()[1].split('/')[-1]
                        elif self._cur.name() == 'java':
                            self._stat['executable'] = self._cur.parent().cmdline()[1].split('/')[-1]
                        else:
                            self._stat['executable'] = self._cur.name() 
                    
                    # determine check-in interval by executable 
                    if self._stat['executable'] == 'bwa':
                        self._interval = 30
                    elif self._stat['executable'] == 'gatk':
                        self._interval = 60
                    else:
                        self._interval = 1
                    
                    cpu_percent = self._cur.cpu_percent()
                    self._stat['avg_cpu_percent'] += cpu_percent
                    self._stat['avg_mem_percent'] += self._cur.memory_percent()
                    self._stat['total_read_count'] = self._cur.io_counters().read_count
                    self._stat['total_write_count'] = self._cur.io_counters().write_count
                    self._stat['total_read_bytes'] = self._cur.io_counters().read_bytes
                    self._stat['total_write_bytes'] = self._cur.io_counters().write_bytes
                    print(self._cur.pid, self._stat['executable'], cpu_percent, self._cur.memory_percent(), self._cur.io_counters())
                    self._msg_q.put({
                        'host': self._hostname,
                        'name': self._name,
                        'expid': self._expid,
                        'timestamp': int(time.time() * 1000),
                        'executable': self._stat['executable'],
                        'cpu_percent': cpu_percent,
                        'memory_percent': self._cur.memory_percent(),
                        'total_read_count': self._stat['total_read_count'],
                        'total_write_count': self._stat['total_write_count'],
                        'total_read_bytes': self._stat['total_read_bytes'],
                        'total_write_bytes': self._stat['total_write_bytes'],
                        'status': 'running',
                    })
                    
                except psutil.NoSuchProcess:
                    self._cur = None
                    with self._lock:
                        self._stat['step'] = 0
                        self._stat['count'] = 0
                        self._stat['executable'] = None 
                        self._stat['runtime'] = 0.0
                        self._stat['avg_cpu_percent']= 0.0
                        self._stat['avg_mem_percent'] = 0.0
                        self._stat['total_read_count'] = 0
                        self._stat['total_write_count'] = 0
                        self._stat['total_read_bytes'] = 0
                        self._stat['total_write_bytes'] = 0
                        self._stat['read_rate'] = 0
                        self._stat['write_rate'] = 0
                        self._stat['timestamp'] = 0
            time.sleep(self._interval)
            
    def _get_walltime(self):
        '''
        Get workflow wall time
        
        :rtype int
        
        '''
        pass

if __name__ == '__main__':
    try:
        ProcessMonitor(
                'genomic', 
                Queue(), 
                set(['bwa', 'java', 'python', 'pegasus-transfer'])).run()
    except KeyboardInterrupt:
        pass
