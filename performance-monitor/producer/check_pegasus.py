import psutil
import time
import pika
import socket
import subprocess
import os
import sys
import re
import shutil
import argparse
import logging
from multiprocessing import Process, Manager, Lock, Queue, Value

from message_sender import MessageSender
from config import MESSAGE_BROKER_URI, CONDOR_EXE_DIR

logging.basicConfig(
                    filename='monitor.log', 
                    format='[%(asctime)s] %(levelname)s  %(processName)s [%(funcName)s:%(lineno)d] %(message)s"', 
                    level=logging.DEBUG)

class WorkflowMonitor(Process):
    '''
    Monitor workflow status
    
    '''
    HEARTBEAT_LIMIT = 30
    
    def __init__(self,  exp_id, workdir_base, run_num, msg_q):
        '''
        
        :param subprocess.Value done: number of done workflows
        :param str workdirs: workflow working directories
        
        '''
        Process.__init__(self)
        self.name = 'WorkflowMonitor'
        self.daemon = True
        self._exp_id = exp_id
        self._workdir_base = workdir_base
        self._run_num = run_num
        self._done = 0
        self._heartbeat = 0
        self._msg_q = msg_q
        self._finished = set()
        
    def run(self):
        '''
        Override
        
        '''
        logging.info('Started')
        while self._done < self._run_num:
            logging.info('Expecting number of runs: %s' % self._run_num)
            logging.info('Number of done jobs: %d' % self._done)
            if os.path.isdir(self._workdir_base):
                workdirs = os.listdir(self._workdir_base)
                for w in workdirs:
                    if w in self._finished: 
                        continue
                    d = '%s%s' % (self._workdir_base, w) if self._workdir_base[-1] == '/' else '%s/%s' % (self._workdir_base, w)
                    if os.path.isdir(d):
                        out, err = subprocess.Popen(('pegasus-status -l %s' % d).split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
                        if not err:
                            for l in out.split('\n'):
                                if re.match('[ \t]+[0-9]+', l):
                                    status = re.split('[ \t]+', l)[9] 
                                    if status != 'Running':
                                        self._finished.add(w)
                                        msg = {
                                                'exp_id': self._exp_id,
                                                'run_id': int(time.time()),
                                                'status': status,
                                                'type': 'run',
                                                'timestamp': time.time(),
                                                'walltime': self._get_walltime(d)
                                            }
                                        self._msg_q.put(msg)
                                        logging.info('Message sent to Message Sender')
                                        logging.debug('Run number: %d\tWalltime: %d\tStatus: %s' % (msg['run_id'], msg['walltime'], msg['status']))
                                        self._done += 1
                                    break
            self._heartbeat += 1
            if self._heartbeat >= self.HEARTBEAT_LIMIT:
                logging.info('Send heartbeat signal to keep the AMQP connection alive')
                self._msg_q.put('alive')
                self._heartbeat = 0
            time.sleep(10)
            
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
            
class SystemMonitor(Process):
    '''
    System resource usage monitor
    
    '''
    
    COUNT_LIMIT = 60 # 5 mins (weird... but lucky number)
    
    def __init__(self, exp_id, hostname, msg_q):
        '''
        
        :param str exp_id: experiment ID
        :param str hostname: hostname
        :param subprocess.Queue msg_q: message queue for sending data to message sender
        
        '''
        Process.__init__(self)
        self.name = 'SystemMonitor'
        self.daemon = True
        self._msg_q = msg_q
        self._init_read_bytes = psutil.disk_io_counters().read_bytes
        self._init_write_bytes  = psutil.disk_io_counters().write_bytes
        self._init_bytes_sent = int(psutil.net_io_counters().bytes_sent)
        self._init_bytes_recv = int(psutil.net_io_counters().bytes_recv)
        self._count = 0
        self._start_time = 0
        self._stat = {
                      'exp_id': exp_id,
                      'host': hostname,
                      'type': 'system',
                      'sys_max_cpu_percent': 0,
                      'sys_min_cpu_percent': 2000,
                      'sys_max_mem_percent': 0,
                      'sys_min_mem_percent': 2000,
            }

    def run(self):
        '''
        Override
        
        '''
        logging.info('Started')
        self._start_time = time.time()
        while True:
            while not os.listdir(CONDOR_EXE_DIR):
                time.sleep(5)
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
            self._count += 1
            
            if self._count >= self.COUNT_LIMIT:
                logging.info('Send message ...')
                self._send()                
            time.sleep(5)
    
    def _send(self):
        '''
        Send system statistics 
        
        '''
        send_time = time.time()
        self._stat['runtime'] = time.time() - self._start_time
        self._start_time = send_time
        self._stat['count'] = self._count
        self._count = 0
        
        self._stat['sys_cpu_percent'] /= self._stat['count']
        self._stat['sys_mem_percent'] /= self._stat['count']
        
        self._stat['sys_read_rate'] = self._stat['sys_read_bytes'] / self._stat['runtime']
        self._stat['sys_write_rate'] = self._stat['sys_write_bytes'] / self._stat['runtime']
        self._stat['sys_send_rate'] = self._stat['sys_net_bytes_sent'] / self._stat['runtime']
        self._stat['sys_recv_rate'] = self._stat['sys_net_bytes_recv'] / self._stat['runtime']
        if self._stat['sys_min_cpu_percent'] == 2000: self._stat['sys_min_cpu_percent'] = 0
        if self._stat['sys_min_mem_percent'] == 2000: self._stat['sys_min_mem_percent'] = 0
        self._stat['timestamp'] = send_time
        logging.info('Message sent to MessageSender')
        logging.debug('Runtime: %f\tCount: %d' % (self._stat['runtime'], self._stat['count']))
        self._msg_q.put(dict(self._stat))
        self._stat['sys_max_cpu_percent'] = 0
        self._stat['sys_min_cpu_percent'] = 2000
        self._stat['sys_max_mem_percent'] = 0
        self._stat['sys_min_mem_percent'] = 2000
        self._stat['sys_cpu_percent'] = 0
        self._stat['sys_mem_percent'] = 0

class WaitProcess(Process):
    '''
    Wait on the termination of a process
    
    '''
    
    def __init__(self, proc, lock, data, msg_q):
        '''
        
        '''
        logging.info('WaitProcess spawned: %d' % proc.pid)
        Process.__init__(self)
        self.name = 'WaitProcess'
        self.daemon = True
        self._proc = proc
        self._lock = lock
        self._stat = data
        self._msg_q = msg_q
        
    def run(self):
        '''
        Starts waiting on a process
        
        '''
        logging.info('WaitProcess started: %d' % self._proc.pid)
        psutil.wait_procs([self._proc], None, self._on_terminate)
    
    def _on_terminate(self, proc):
        '''
        Sends data to the message sender when a monitored job is done
        
        :param psutil.Process: a monitored condor_startd process
        
        '''
        logging.debug('Job terminated: %d' % proc.pid)
        logging.debug('Waiting Jobs: %s' % str(self._stat.keys()))
        if proc not in self._stat or not self._stat[proc.pid]:
            logging.warning('Job %d is not of interest. Quit' % proc.pid)
            return
        if 'cmdline' not in self._stat[proc.pid] or not self._stat[proc.pid]['cmdline']: 
            logging.warning('Cmdline not available for %d. Quit' % proc.pid)
            return
        with self._lock:
            self._stat[proc.pid]['timestamp'] = time.time()
            self._stat[proc.pid]['runtime'] = self._stat[proc.pid]['timestamp'] - proc.create_time() 
            if self._stat[proc.pid]['count'] > 1:
                self._stat[proc.pid]['avg_cpu_percent'] /= self._stat[proc.pid]['count'] - 1 
                self._stat[proc.pid]['avg_mem_percent'] /= self._stat[proc.pid]['count']
            else:
                self._stat[proc.pid]['avg_cpu_percent'] = 0
                self._stat[proc.pid]['avg_mem_percent'] = 0
            if self._stat[proc.pid]['min_cpu_percent'] == 2000:
                self._stat[proc.pid]['min_cpu_percent'] = 0
            if self._stat[proc.pid]['min_mem_percent'] == 2000:
                self._stat[proc.pid]['min_mem_percent'] = 0
            self._msg_q.put(dict(self._stat[proc.pid]))
        logging.info('Message sent to MessageSender')
        logging.debug('Runtime: %f\tCount: %d' % (self._stat[proc.pid]['runtime'], self._stat[proc.pid]['count']))

class JobMonitor(Process):
    '''
    A monitor to check a list of processes' system resource utilization
    
    '''
    def __init__(self, exp_id, hostname, msg_q, execs, stat):
        '''
        Init

        :param str exp_id: experiment ID
        :param str hostname: hostname
        :param set executables: executables to be monitored
        
        '''
        Process.__init__(self)
        self.name = 'JobMonitor'
        self._exp_id = exp_id
        self._hostname = hostname
        self._msg_q = msg_q
        self._cur = None
        self._lock = Lock()
        self._jobs = set(execs)
        self._stat = stat
        self._cur_stat = None
        self._cur_job = 0
        
    def _find_process(self):
        '''
        Find any running process of interest. Because only an interesting job will be running at 
        any point of time, it simply returns the first found process of interest
        
        :rtype - psutil.Process
        
        '''
        logging.info('Looking for condor_startd')
        pid = self._get_startd_pid()
        if not pid: 
            logging.info('No condor_startd found')
            return None
        logging.debug('PID: %d' % pid)
        logging.debug('Waiting processes: %s' % str(self._stat.keys()))
        proc = psutil.Process(pid)
        if pid not in self._stat:
            logging.info('%d is not in the waiting list' % pid)
            with self._lock:
                self._stat[pid] = None
                wp = WaitProcess(proc, self._lock, self._stat, self._msg_q)
                wp.start()
        try:
            logging.info('Looking for interesting job')
            children = proc.children(recursive=True)
            logging.debug('Children: %s' % str(children))
            for p in children:
                try:
                    executable = None                
                    logging.debug('Command line of %d: %s' % (p.pid, ' '.join(p.cmdline())))
                    if p.name() == 'python':
                        executable = p.cmdline()[1].split('/')[-1] if len(p.cmdline()) > 1 else None
                    elif p.name() == 'java':
                        executable = p.parent().cmdline()[1].split('/')[-1] if len(p.parent().cmdline()) > 1 else None
                    else:
                        executable = p.name()
                    logging.debug('Executable: %s' % executable)
                    if executable and executable in self._jobs:
                        logging.debug('Interesting job found: %s' % p.pid)
                        if self._cur_job != proc.pid:
                            logging.info('New job is found. Change job name')
                            cmd = None
                            parent_cmd = None
                            try:
                                cmd = list(p.cmdline())
                                parent_cmd = list(p.parent().cmdline())
                            except psutil.NoSuchProcess:
                                logging.debug('Process %d is gone when just being found. Skip' % p.pid)
                            else:
                                self._cur_stat = {
                                    'exp_id': self._exp_id,
                                    'host': self._hostname,
                                    'type': 'job',
                                    'avg_cpu_percent': 0,
                                    'avg_mem_percent': 0,
                                    'max_cpu_percent': 0,
                                    'min_cpu_percent': 2000,
                                    'max_mem_percent': 0,
                                    'min_mem_percent': 2000,
                                    'count': 0
                                }
                                if p.name() == 'python':
                                    self._cur_stat['cmdline'] = ' '.join([arg.split('/')[-1] for arg in cmd[1:3]])
                                elif p.name() == 'java':
                                    self._cur_stat['cmdline'] = ' '.join([arg.split('/')[-1] for arg in parent_cmd[1:3]])
                                else:
                                     self._cur_stat['cmdline'] = ' '.join([arg.split('/')[-1] for arg in cmd[:2]])
                                logging.info('Message dict created')
                                logging.debug('Cmdline: %s' % self._cur_stat['cmdline'])
                                self._cur_job = proc.pid
                        else:
                            logging.info('Old job. Not change job name')
                        return p
                except psutil.NoSuchProcess:
                    logging.debug('Process %d is gone when just being found. Skip' % p.pid)
        except psutil.NoSuchProcess:
            logging.info('Monitored job %d is gone in the middle' % proc.pid) 
        return None

    def run(self):
        '''
        Start the monitor. It creates an AMQP sender and sends job statistics periodically
         
        '''
        while True:
            while not self._cur: 
                self._cur = self._find_process()
                time.sleep(1)
            name = None
            cmdline = None
            cpu_pct = 0
            mem_pct = 0
            r_bytes = 0
            w_bytes = 0
            try:
                cpu_pct = self._cur.cpu_percent()
                mem_pct = self._cur.memory_percent()
                self._cur_stat['max_cpu_percent'] = max(self._cur_stat['max_cpu_percent'], cpu_pct)
                if cpu_pct:
                    self._cur_stat['min_cpu_percent'] = min(self._cur_stat['min_cpu_percent'], cpu_pct)
                self._cur_stat['avg_cpu_percent'] += cpu_pct
                self._cur_stat['max_mem_percent'] = max(self._cur_stat['max_mem_percent'], mem_pct)
                self._cur_stat['min_mem_percent'] = min(self._cur_self._cur_stat['min_mem_percent'], mem_pct)
                self._cur_stat['avg_mem_percent'] += mem_pct
                self._cur_stat['total_read_bytes'] = self._cur.io_counters().read_bytes
                self._cur_stat['total_write_bytes'] = self._cur.io_counters().write_bytes
                self._cur_stat['count'] += 1
            except psutil.NoSuchProcess:
                logging.debug('Job %d is gone in the middle of examination' % self._cur.pid)
                self._cur = None
            else:
                with self._lock:
                    self._stat[self._cur_job] = dict(self._cur_stat)
            time.sleep(1)
            
    def _get_startd_pid(self):
        '''
        '''
        return int(os.listdir(CONDOR_EXE_DIR)[0][4:]) if os.listdir(CONDOR_EXE_DIR) else None

    
class MonitorManager(object):
    '''
    Manages the monitors
    
    '''
    
    def __init__(self, exp_id, is_master, is_worker, work_dir=None, run=0, execs=None):
        '''
        
        '''
        self._exp_id = exp_id
        self._msg_q = Queue()
        self._hostname = socket.gethostname()
        self._sender = MessageSender(
                self._exp_id,
                pika.URLParameters(MESSAGE_BROKER_URI), 
                self._msg_q,
                self._hostname,
                )
        self._is_master = is_master
        self._is_worker = is_worker
        self._stat = Manager().dict()
        if self._is_master:
            if not work_dir:
                logging.error('Workflow directory not provided')
                raise RuntimeError('Workflow working directory must not be none or empty for master nodes')
            if not run:
                logging.error('Run number not provided')
                raise RuntimeError('Run number must not be zero for master nodes')
            self._workflow_monitor = WorkflowMonitor(self._exp_id, work_dir, run, self._msg_q)
        if self._is_worker:
            if not execs:
                logging.error('Executable list not provided')
                raise RuntimeError('Executables to be tracked must be provided for worker nodes')
            self._sys_monitor = SystemMonitor(self._exp_id, self._hostname, self._msg_q)
            self._job_monitor = JobMonitor(self._exp_id, self._hostname, self._msg_q, execs, self._stat)
    
    def run(self):
        '''
        Starts MonitorManager
        '''
        self._sender.start()
        if self._is_master:
            logging.info('WorkflowMonitor started')
            self._workflow_monitor.start()
        if self._is_worker:
            logging.info('Say hello')
            self._msg_q.put({
                    'exp_id': self._exp_id,
                    'type': 'worker',
                    'host': self._hostname,
                    'timestamp': int(time.time()),
                })
            logging.info('SystemMonitor started')
            self._sys_monitor.start()
            logging.info('JobMonitor started')
            self._job_monitor.start()
        while True: 
            pass
    
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
        
        MonitorManager(
                args.exp_id,
                args.is_master,
                args.is_worker,
                args.workdir_base,
                args.run_num,
                args.executables,
            ).run()
    except KeyboardInterrupt:
        logging.warning('Ctrl-c found. Exit')
    except:
        logging.error('Unexpected error: %s\n Exit' % str(sys.exc_info[0]))
