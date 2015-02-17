import psutil
import time
import pika
import socket
import subprocess
import os
import re
import shutil
import argparse
import logging
from multiprocessing import Process, Manager, Queue

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
    HEARTBEAT_LIMIT = 15
    
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
            logging.info('Number of finished runs: %d' % self._done)
            if os.path.isdir(self._workdir_base):
                workdirs = os.listdir(self._workdir_base)
                for w in workdirs:
                    if w in self._finished: 
                        continue
                    d = '%s%s' % (self._workdir_base, w) if self._workdir_base[-1] == '/' else '%s/%s' % (self._workdir_base, w)
                    if os.path.isdir(d):
                        out, err = subprocess.Popen(('pegasus-status -l %s' % d).split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
                        if err:
                            logging.debug('Error occurs during executing "pegasus-statistics": %s' % err)
                            continue
                        for l in out.split('\n'):
                            if re.match('[ \t]+[0-9]+', l):
                                status = re.split('[ \t]+', l)[9] 
                                if status != 'Running':
                                    walltime = self._get_walltime(d)
                                    if not walltime:
                                        logging.warning('Walltime is not available')
                                        logging.debug('Status: %s' % status)
                                        continue;
                                    self._finished.add(w)
                                    msg = {
                                            'exp_id': self._exp_id,
                                            'run_id': int(time.time()),
                                            'status': status,
                                            'type': 'run',
                                            'timestamp': time.time(),
                                            'walltime': walltime
                                        }
                                    self._msg_q.put(msg)
                                    logging.info('Message sent to Message Sender')
                                    if msg['walltime']:
                                        logging.debug('Run number: %d\tWalltime: %d\tStatus: %s' % (msg['run_id'], msg['walltime'], msg['status']))
                                    else:
                                        logging.debug('Run number: %d\tStatus: %s' % (msg['run_id'], msg['status']))
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
            cpu_pct, mem_pct = psutil.cpu_percent(), psutil.virtual_memory().percent
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
        self._init_read_bytes = self._stat['sys_read_bytes']
        self._init_write_bytes = self._stat['sys_write_bytes']
        self._init_bytes_sent = self._stat['sys_net_bytes_sent']
        self._init_bytes_recv = self._stat['sys_net_bytes_recv']

class WaitProcess(Process):
    '''
    Wait on the termination of a process
    
    '''
    
    def __init__(self, proc, data, msg_q):
        '''
        
        '''
        logging.info('WaitProcess spawned: %d' % proc.pid)
        Process.__init__(self)
        self.name = 'WaitProcess'
        self.daemon = True
        self._proc = proc
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
        if proc.pid not in self._stat or not self._stat[proc.pid]:
            logging.warning('Job %d is not of interest. Quit' % proc.pid)
            return
        msg = dict(self._stat[proc.pid])
        del self._stat[proc.pid]
        logging.debug('Copied job message: %s' % str(msg))
        msg['timestamp'] = time.time()
        msg['runtime'] = msg['timestamp'] - proc.create_time() 
        msg['avg_cpu_percent'] /= msg['count'] 
        msg['avg_mem_percent'] /= msg['count']
        msg['read_rate'] = msg['total_read_bytes'] / msg['runtime']
        msg['write_rate'] = msg['total_write_bytes'] / msg['runtime']
        msg['send_rate'] = msg['total_bytes_sent'] / msg['runtime']
        msg['recv_rate'] = msg['total_bytes_recv'] / msg['runtime']
        self._msg_q.put(dict(msg))
        logging.info('Message sent to MessageSender')
        logging.debug('Runtime: %f\tCount: %d' % (msg['runtime'], msg['count']))

class JobMonitor(Process):
    '''
    A monitor to check a list of processes' system resource utilization
    
    '''
    def __init__(self, exp_id, hostname, msg_q):
        '''
        Init

        :param str exp_id: experiment ID
        :param str hostname: hostname
        
        '''
        Process.__init__(self)
        self.name = 'JobMonitor'
        self._exp_id = exp_id
        self._hostname = hostname
        self._msg_q = msg_q
        self._stat = Manager().dict()
        
    def _find_process(self):
        '''
        Find any running process of interest. Because only an interesting job will be running at 
        any point of time, it simply returns the first found process of interest
        
        '''
        logging.info('Looking for condor_startd')
        pid = self._get_startd_pid()
        while not pid: 
            time.sleep(1)
            pid = self._get_startd_pid()
            
        logging.debug('PID: %d' % pid)
        proc = psutil.Process(pid)

        logging.info('Looking for job name')
        job_name = self._get_job_name()
        while not job_name:
            time.sleep(1)
            job_name = self._get_job_name()
        
        if pid not in self._stat:
            logging.info('%d is not in the waiting list' % pid)
            self._stat[pid] = None
            wp = WaitProcess(proc, self._stat, self._msg_q)
            wp.start()
            cpu_pct, mem_pct = psutil.cpu_percent(), psutil.virtual_memory().percent
            self._stat[pid] = {
                    'exp_id': self._exp_id,
                    'host': self._hostname,
                    'name': job_name,
                    'type': 'job',
                    'avg_cpu_percent': cpu_pct,
                    'avg_mem_percent': mem_pct,
                    'max_cpu_percent': cpu_pct,
                    'min_cpu_percent': cpu_pct,
                    'max_mem_percent': mem_pct,
                    'min_mem_percent': mem_pct,
                    'init_read_bytes': psutil.disk_io_counters().read_bytes,
                    'init_write_bytes': psutil.disk_io_counters().write_bytes,
                    'init_bytes_sent': psutil.net_io_counters().bytes_sent,
                    'init_bytes_recv': psutil.net_io_counters().bytes_recv,
                    'count': 1
            }
            return proc

    def run(self):
        '''
        Start the monitor. It creates an AMQP sender and sends job statistics periodically
         
        '''
        while True:
            cur = self._find_process()
            logging.info('Start monitoring ...')
            while cur.is_running():
                pid = cur.pid
                cpu_pct, mem_pct = psutil.cpu_percent(), psutil.virtual_memory().percent
                self._stat[pid]['max_cpu_percent'] = max(self._stat[pid]['max_cpu_percent'], cpu_pct)
                self._stat[pid]['min_cpu_percent'] = min(self._stat[pid]['min_cpu_percent'], cpu_pct)
                self._stat[pid]['avg_cpu_percent'] += cpu_pct
                self._stat[pid]['max_mem_percent'] = max(self._stat[pid]['max_mem_percent'], mem_pct)
                self._stat[pid]['min_mem_percent'] = min(self._stat[pid]['min_mem_percent'], mem_pct)
                self._stat[pid]['avg_mem_percent'] += mem_pct
                self._stat[pid]['total_read_bytes'] = psutil.disk_io_counters().read_bytes - self._stat[pid]['init_read_bytes']
                self._stat[pid]['total_write_bytes'] = psutil.disk_io_counters().write_bytes - self._stat[pid]['init_write_bytes']
                self._stat[pid]['total_bytes_sent'] = psutil.net_io_counters().bytes_sent - self._stat[pid]['init_bytes_sent']
                self._stat[pid]['total_bytes_recv'] = psutil.net_io_counters().bytes_recv - self._stat[pid]['init_bytes_recv']
                self._stat[pid]['count'] += 1
                time.sleep(1)
            logging.info('%d is gone' % cur.pid)
            
    def _get_startd_pid(self):
        '''
        '''
        return int(os.listdir(CONDOR_EXE_DIR)[0][4:]) if os.listdir(CONDOR_EXE_DIR) else None
    
    def _get_job_name(self):
        '''
        
        '''
        job_ad_path = '%s/%s/.job.ad' % (CONDOR_EXE_DIR, os.listdir(CONDOR_EXE_DIR)[0])
        if os.path.exists(job_ad_path): 
            with open(job_ad_path, 'r') as job_ad:
                for l in job_ad:
                    if 'DAGNodeName' in l:
                        return re.sub('[ "]', '', l.split('=')[1])
        else:
            return None
        
                    
    
class MonitorManager(object):
    '''
    Manages the monitors
    
    '''
    
    def __init__(self, exp_id, is_master, is_worker, site=None, work_dir=None, run=0):
        '''
        
        '''
        self._exp_id = exp_id
        self._msg_q = Queue()
        self._hostname = socket.gethostname()
        self._site = site
        self._sender = MessageSender(
                self._exp_id,
                pika.URLParameters(MESSAGE_BROKER_URI), 
                self._msg_q,
                self._hostname,
                )
        self._is_master = is_master
        self._is_worker = is_worker
        if self._is_master:
            if not work_dir:
                logging.error('Workflow directory not provided')
                raise RuntimeError('Workflow working directory must not be none or empty for master nodes')
            if not run:
                logging.error('Run number not provided')
                raise RuntimeError('Run number must not be zero for master nodes')
            self._workflow_monitor = WorkflowMonitor(self._exp_id, work_dir, run, self._msg_q)
        if self._is_worker:
            self._sys_monitor = SystemMonitor(self._exp_id, self._hostname, self._msg_q)
            self._job_monitor = JobMonitor(self._exp_id, self._hostname, self._msg_q)
    
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
                    'site': self._site,
                    'host': self._hostname,
                    'timestamp': int(time.time()),
                })
            logging.info('SystemMonitor started')
            self._sys_monitor.start()
            logging.info('JobMonitor started')
            self._job_monitor.start()
        while True:  pass
    
if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--id', dest='exp_id', type=str, help='Experiment ID', required=True)
        parser.add_argument('-m', '--master', dest='is_master', default=False, action='store_true', help='Master')
        parser.add_argument('-w', '--worker', dest='is_worker', default=False, action='store_true', help='Worker')
        parser.add_argument('-d', '--dir', dest='workdir_base', type=str, help='Workflow working directory base')
        parser.add_argument('-r', '--run-num', dest='run_num', type=int, help='Number of planned runs')
        parser.add_argument('-s', '--site', type=str, dest='site', help='The site the node is running on')
        args = parser.parse_args()
        
        MonitorManager(
                args.exp_id,
                args.is_master,
                args.is_worker,
                args.site,
                args.workdir_base,
                args.run_num,
            ).run()
    except KeyboardInterrupt:
        logging.warning('Ctrl-c found. Exit')
    except:
        logging.exception('Unexpected exception')
