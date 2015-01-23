'''
Created on Jan 13, 2015

@author: dc
'''
import json
import uuid
import jinja2
import time
import tornado.web
from config import DB_NAME, check_content_type

class WorkflowsRenderer(tornado.web.RedirectHandler):
    '''
    Renders worklow listing
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
    
    def get(self):
        '''
        GET method
        
        '''
        data = {
                'topology': [t for t in self._db[DB_NAME]['workflow']['topology'].find(fields={'_id': 0})],
                'mode': [m for m in self._db[DB_NAME]['workflow']['mode'].find(fields={'_id': 0})],
                'site': [s for s in self._db[DB_NAME]['workflow']['site'].find(fields={'_id': 0})],
                'worker_size': [w for w in self._db[DB_NAME]['workflow']['vm_size'].find(fields={'_id': 0})],
                'storage_site': [ss for ss in self._db[DB_NAME]['workflow']['storage_site'].find(fields={'_id': 0})],
                'storage_type': [st for st in self._db[DB_NAME]['workflow']['storage_type'].find(fields={'_id': 0})],
            }
        self.render('workflows.html', workflows=[w for w in self._db[DB_NAME]['workflow']['type'].find({}, {'_id': 0}).sort('name')], data=data)
    
    def post(self):
        '''
        POST method: create new experiment
        
        '''
        if not check_content_type(self):
            return
        data = json.loads(self.request.body)
        if not self._db[DB_NAME]['workflow']['manifest'].find_one({
                'type': data['type'],
                'mode': data['mode'],
                'storage_site': data['storage_site'],
                'storage_type': data['storage_type'],
            }):
            self.set_status(404, 'Manifest not available yet')
            return
        data['exp_id'] = str(uuid.uuid4())
        data['status'] = 'submitted'
        data['create_time'] = int(time.time())
        self._db[DB_NAME]['workflow']['experiment'].insert(data)
        self.write({
                'exp_id': data['exp_id'],
                'type': data['type'],
            })
        
class ExperimentRenderer(tornado.web.RedirectHandler):
    '''
    Renders specific experiment info
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
    
    def get(self, workflow, exp_id):
        '''
        GET method: renders experiment page
        
        '''
        exp = self._db[DB_NAME]['workflow']['experiment'].find_one({'exp_id': exp_id}, {'_id': 0})
        if not exp:
            self.set_status(404, 'Experiment not found')
            return 
        if not check_content_type(self):
            return
        content_type = self.request.headers.get('Content-Type') 
        t = self._db[DB_NAME]['workflow']['manifest'].find_one({
                    'type': exp['type'],
                    'mode': exp['mode'],
                    'storage_site': exp['storage_site'],
                    'storage_type': exp['storage_type'],
                    }, {'_id': 0})
        if not t:
            self.set_status(404, 'Manifest not available yet')
            return
        template = t['manifest'] 
        if exp['mode'] == 'multinode' and not exp['bandwidth']:
            exp['bandwidth'] = 500000000
        if exp['storage_site'] == 'remote' and not exp['storage_size']:
            exp['storage_size'] = 50
        exp['resource_type'] = 'BareMetalCE' if exp['worker_size'] == 'ExoGENI-M4' else 'VM'
        if not content_type:
            exp['executables'] = self._db[DB_NAME]['workflow']['type'].find_one({'name': workflow}, {'_id': 0})['executables']
            manifest = jinja2.Template(template).render(param=exp)
            exp['worker_size'] = self._db[DB_NAME]['workflow']['vm_size'].find_one({'value': exp['worker_size']}, {'_id': 0})['name']
            exp['create_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp['create_time']))
            exp['workers'] = [w for w in self._db[DB_NAME]['experiment']['worker'].find({'exp_id': exp_id}, {'_id': 0}).sort('host')]
            exp['runs'] = [r for r in self._db[DB_NAME]['experiment']['run'].find({'exp_id': exp_id}, {'_id': 0}).sort('run_id')]
            if exp['bandwidth']: exp['bandwidth'] /= (1000 * 1000)
            self.render('experiment.html', manifest=manifest, data=exp, current_uri=self.request.uri)
        elif content_type == 'application/json':
            del exp['create_time']
            del exp['status']
            del exp['exp_id']
            self.write(exp)

    def post(self, workflow, exp_id):
        '''
        POST method: provides manifest download
        
        '''
        exp = self._db[DB_NAME]['workflow']['experiment'].find_one({'exp_id': exp_id}, {'_id': 0})
        if not exp:
            self.set_status(404, 'Experiment not found')
            return 
        template = self._db[DB_NAME]['workflow']['manifest'].find_one({
                    'type': exp['type'],
                    'mode': exp['mode'],
                    'storage_site': exp['storage_site'],
                    'storage_type': exp['storage_type'],
                    }, {'_id': 0})['manifest']
        if exp['mode'] == 'multinode' and not exp['bandwidth']:
            exp['bandwidth'] = 500000000
        if exp['storage_site'] == 'remote' and not exp['storage_size']:
            exp['storage_size'] = 50
        exp['executables'] = self._db[DB_NAME]['workflow']['type'].find_one({'name': workflow}, {'_id': 0})['executables']
        manifest = jinja2.Template(template).render(param=exp)
        self.set_header('Content-Type', 'application/rdf+xml')
        self.set_header('Content-Disposition', 'attachment;filename=%s' % '-'.join([exp['type'], exp['topology'], exp['mode'], exp['worker_size'], exp['master_site']]))
        self.write(manifest)
        
    def delete(self, workflow, exp_id):
        '''
        DELETE method: delete an experiment
        
        '''
        if not check_content_type(self):
            return
        if not self.request.body:
            self.set_status(400, 'No action specified')
            return 
        param = json.loads(self.request.body)
        if param['action'] not in set(['remove', 'redo']):
            self.set_status(400, 'Unknown action')
            return 
        if param['action'] == 'remove':
            self._db[DB_NAME]['workflow']['experiment'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['worker'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['job'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['system'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['run'].remove({'exp_id': exp_id})
        
class RunsRenderer(tornado.web.RedirectHandler):
    '''
    Renders runs
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
        
    def post(self, workflow, exp_id):
        '''
        POST method: get run related info
        
        '''
        if not self._db[DB_NAME]['workflow']['experiment'].find({'exp_id': exp_id}).count():
            self.set_status(404, 'Experiment not found')
        runs = [r for r in self._db[DB_NAME]['experiment']['run'].find({'exp_id': exp_id}, {'_id': 0})]
        if not runs:
            self.set_status(204, 'No finished runs')
            return
        self.write({
                'label': [r['run_id'] for r in runs],
                'walltime': [r['walltime'] for r in runs]
            })
        
class WorkerRenderer(tornado.web.RedirectHandler):
    '''
    Renders worker specific info
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
        
    def get(self, workflow, exp_id, worker):
        '''
        GET method: renders worker page
        
        '''
        if not self._db[DB_NAME]['experiment']['worker'].find({'exp_id': exp_id}).count():
            self.set_status(404, 'Experiment or worker not found')
            return
        self.render('worker.html', worker=worker)
    
    def post(self, workflow, exp_id, worker):
        '''
        POST method: returns performance data
        
        '''
        if not check_content_type(self):
            return
        data = json.loads(self.request.body)
        if not self._db[DB_NAME]['workflow']['experiment'].find().count():
            self.set_status(404, 'Experiment not found')
            return
        if not data or 'aspect' not in data:
            self.set_status(422, 'No query identified')
            return
        if data['aspect'] != 'system' and data['aspect'] != 'job':
            self.set_status(422, 'Unknown query')
            return
        stat = [s for s in self._db[DB_NAME]['experiment'][data['aspect']].find({'exp_id': exp_id, 'host': worker}, {'_id': 0}).sort('timestamp')]
        if not stat or len(stat) < 2:
            self.set_status(204, 'Data not available yet')
            return
        res = {}
        if data['aspect'] == 'system':
            res['label'] = [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s['timestamp'])) for s in stat ]
            res['sys_cpu_percent'] = [s['sys_cpu_percent'] for s in stat]
            res['sys_max_cpu_percent'] = [s['sys_max_cpu_percent'] for s in stat]
            res['sys_min_cpu_percent'] = [s['sys_min_cpu_percent'] for s in stat]
            res['sys_max_mem_percent'] = [s['sys_max_mem_percent'] for s in stat]
            res['sys_min_mem_percent'] = [s['sys_min_mem_percent'] for s in stat]
            res['sys_mem_percent'] = [s['sys_mem_percent'] for s in stat]
            res['sys_read_rate'] = [s['sys_read_rate'] for s in stat]
            res['sys_write_rate'] = [s['sys_write_rate'] for s in stat]
            res['sys_send_rate'] = [s['sys_send_rate'] for s in stat]
            res['sys_recv_rate'] = [s['sys_recv_rate'] for s in stat]
        else:
            res['label'] = [s['cmdline'] for s in stat]
            res['avg_cpu_percent'] = [s['avg_cpu_percent'] for s in stat]
            res['max_cpu_percent'] = [s['max_cpu_percent'] for s in stat]
            res['min_cpu_percent'] = [s['min_cpu_percent'] for s in stat]
            res['max_mem_percent'] = [s['max_mem_percent'] for s in stat]
            res['min_mem_percent'] = [s['min_mem_percent'] for s in stat]
            res['avg_mem_percent'] = [s['avg_mem_percent'] for s in stat]
            res['runtime'] = [s['runtime'] for s in stat]
            res['read_rate'] = [s['total_read_bytes'] / s['runtime'] for s in stat]
            res['write_rate'] = [s['total_write_bytes'] / s['runtime'] for s in stat]
            res['total_read_bytes'] = [s['total_read_bytes'] for s in stat]
            res['total_write_bytes'] = [s['total_write_bytes'] for s in stat]
        
        self.write(res)
        
class WorkflowRenderer(tornado.web.RequestHandler):
    '''
    Renders experiment listing
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
        
    def get(self, workflow):
        '''
        GET method: renders experiments listing page
        
        '''
        exp = [e for e in self._db[DB_NAME]['workflow']['experiment'].find({'type': workflow}, {'_id': 0})]
        for e in exp:
            if e['status'] == 'submitted':
                runs = self._db[DB_NAME]['experiment']['run'].find_one({'exp_id': e['exp_id']})
                if runs.count() > 0 and runs.count() == exp['run_num']:
                    e['status'] = 'finished'
                elif self._db[DB_NAME]['experiment']['worker'].find_one({'exp_id': e['exp_id']}):
                    e['status'] = 'running'
                if e['status'] != 'submitted':    
                    self._db[DB_NAME]['workflow']['experiment'].update({'exp_id': e['exp_id']}, {'$set': {'status': e['status']}})
        self.render('experiments.html', experiments=exp, current_uri=self.request.uri)

