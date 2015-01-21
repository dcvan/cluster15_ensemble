'''
Created on Jan 13, 2015

@author: dc
'''
import json
import uuid
import jinja2
import time
import tornado.web
from config import DB_NAME

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
                'topology': [t for t in self._db[DB_NAME]['workflow']['topology'].find({}, {'_id': 0})],
                'mode': [m for m in self._db[DB_NAME]['workflow']['mode'].find({}, {'_id': 0})],
                'worker_size': [w for w in self._db[DB_NAME]['workflow']['vm_size'].find({}, {'_id': 0})],
                'storage_site': [ss for ss in self._db[DB_NAME]['workflow']['storage_site'].find({}, {'_id': 0})],
                'storage_type': [st for st in self._db[DB_NAME]['workflow']['storage_type'].find({}, {'_id': 0})],
            }
        self.render('workflows.html', workflows=[w for w in self._db[DB_NAME]['workflow']['type'].find({}, {'_id': 0}).sort('name')], data=data)
    
    def post(self):
        '''
        POST method
        
        '''
        data = json.loads(self.request.body)
        data['exp_id'] = str(uuid.uuid4())
        data['status'] = 'submitted'
        data['create_time'] = int(time.time())
        self._db[DB_NAME][data['exp_id']]['info'].insert(data)
        self.set_header('Content-Type', 'application/json;charset="utf-8"')
        self.write(json.dumps({
                'exp_id': data['exp_id'],
                'type': data['type'],
            }))
        
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
        exp = self._db[DB_NAME][exp_id]['info'].find_one(fields={'_id': 0})
        if not exp:
            self.set_status(404, 'Experiment not found')
            return 
        template = self._db[DB_NAME]['workflow']['manifest'].find_one({
                    'type': exp['type'],
                    'topology': exp['topology'],
                    'mode': exp['mode'],
                    'storage_site': exp['storage_site'],
                    'storage_type': exp['storage_type'],
                    }, {'_id': 0})['manifest']
        if exp['mode'] == 'multinode' and not exp['bandwidth']:
            exp['bandwidth'] = 500000000
        if exp['storage_site'] == 'remote' and not exp['storage_size']:
            exp['storage_size'] = 50
        exp['resource_type'] = 'BareMetalCE' if exp['worker_size'] == 'ExoGENI-M4' else 'VM'
        exp['executables'] = self._db[DB_NAME]['workflow']['type'].find_one({'name': workflow}, {'_id': 0})['executables']
        manifest = jinja2.Template(template).render(param=exp)
        exp['worker_size'] = self._db[DB_NAME]['workflow']['vm_size'].find_one({'value': exp['worker_size']}, {'_id': 0})['name']
        exp['create_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp['create_time']))
        exp['workers'] = [w for w in self._db[DB_NAME][exp_id]['worker'].find(fields={'_id': 0})]
        exp['runs'] = [r for r in self._db[DB_NAME][exp_id]['run'].find(fields={'_id': 0})]
        if exp['bandwidth']: exp['bandwidth'] /= (1000 * 1000)
        self.render('experiment.html', manifest=manifest, data=exp, current_uri=self.request.uri)

    def post(self, workflow, exp_id):
        '''
        POST method: provides manifest download
        
        '''
        exp = self._db[DB_NAME][exp_id]['info'].find_one(fields={'_id': 0})
        if not exp:
            self.set_status(404, 'Experiment not found')
            return 
        template = self._db[DB_NAME]['workflow']['manifest'].find_one({
                    'type': exp['type'],
                    'topology': exp['topology'],
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
        self.set_header('Content-Disposition', 'attachment;filename=%s' % '-'.join([exp['type'], exp['topology'], exp['mode']]))
        self.write(manifest)
        
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
        if not self._db[DB_NAME][exp_id]['info'].find().count():
            self.set_status(404, 'Experiment not found')
        runs = [r for r in self._db[DB_NAME][exp_id]['run'].find(fields={'_id': 0})]
        if not runs:
            self.set_status(204, 'No finished runs')
            return
        self.set_header('Content-Type', 'application/json;charset="utf-8"')
        self.write(json.dumps({'runs': runs}))
        
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
        if not self._db[DB_NAME][exp_id]['worker'].find().count():
            self.set_status(404, 'Experiment or worker not found')
            return
        self.render('worker.html', worker=worker)
    
    def post(self, workflow, exp_id, worker):
        '''
        POST method: returns performance data
        
        '''
        data = json.loads(self.request.body)
        if not self._db[DB_NAME][exp_id]['info'].find().count():
            self.set_status(404, 'Experiment not found')
            return
        if not data or 'aspect' not in data:
            self.set_status(422, 'No query identified')
            return
        if data['aspect'] != 'system' and data['aspect'] != 'process':
            self.set_status(422, 'Unknown query')
        stat = [s for s in self._db[DB_NAME][exp_id][data['aspect']].find({'host': worker}, {'_id': 0}).sort('timestamp')]
        if not stat or len(stat) < 2:
            self.set_status(204, 'Data not available yet')
            self.write(None)
        res = {}
        if data['aspect'] == 'system':
            res['label'] = [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat[i]['timestamp'])) if i == 0 or i == len(stat) - 1 else '' for i in range(0, len(stat))]
            res['sys_cpu_percent'] = [s['sys_cpu_percent'] for s in stat]
            res['sys_mem_percent'] = [s['sys_mem_percent'] for s in stat]
            res['sys_read_bytes'] = [s['sys_read_bytes'] for s in stat]
            res['sys_write_bytes'] = [s['sys_write_bytes'] for s in stat]
            res['sys_net_bytes_sent'] = [s['sys_net_bytes_sent'] for s in stat]
            res['sys_net_bytes_recv'] = [s['sys_net_bytes_recv'] for s in stat]

        else:
            res['label_running'] = [s['cmdline'].split( )[0] if s['status'] == 'started' else '' for s in stat]
            res['label_terminated'] = [s['cmdline'].split(' ')[0] for s in stat if s['status'] == 'terminated']
            res['avg_cpu_percent'] = [s['avg_cpu_percent'] for s in stat if s['status'] == 'terminated']
            res['avg_mem_percent'] = [s['avg_mem_percent'] for s in stat if s['status'] == 'terminated']
            res['runtime'] = [s['runtime'] for s in stat if s['status'] == 'terminated']
            res['read_rate'] = [s['total_read_bytes'] / s['runtime'] for s in stat if s['status'] == 'terminated']
            res['write_rate'] = [s['total_write_bytes'] / s['runtime'] for s in stat if s['status'] == 'terminated']
            res['cpu_percent'] = [s['cpu_percent'] for s in stat if s['status'] != 'terminated']
            res['mem_percent'] = [s['memory_percent'] for s in stat if s['status'] != 'terminated']
            res['total_read_bytes'] = [s['total_read_bytes'] for s in stat if s['status'] != 'terminated']
            res['total_write_bytes'] = [s['total_write_bytes'] for s in stat if s['status'] != 'terminated']
        
        self.set_header('Content-Type', 'application/json;charset="utf-8"')
        self.write(json.dumps(res))
        
class WorkflowRender(tornado.web.RedirectHandler):
    '''
    Renders workflow listing
    
    '''
    
    def initialize(self, db):
        '''
        Init
        
        :param pymongo.MongoClient db: the mongoDB connection
        
        '''
        self._db = db
        
    def get(self):
        '''
        GET method
        
        '''
        rs = self._db[DB_NAME]['workflow'].find().sort('name')
        self.render('workflow.html', workflows=[w for w in rs])
        
class JobRender(tornado.web.RedirectHandler):
    '''
    Renders job stat
    
    '''
    
    def initialize(self, db):
        '''
        Init
        
        :param pymongo.MongoClient db: the mongoDB connection
        
        '''
        self._db = db
        
    def post(self, name, job_id):
        '''
        POST method
        
        '''
        rs = self._db[DB_NAME]['update'].find({
              'name': name,
              'job_id': job_id,
              'status': 'terminated'
            }).sort('start_time')
        if rs.count() != 0:
            self.set_header('Content-Type', 'application/json;charset="utf-8"')
            data = []
            for d in rs:
                del d['_id']
                data.append(d)
            self.write(json.dumps(data))
        else:
            self.set_status(404)
        self.finish()
        
class ExperimentStatusRenderer(tornado.web.RedirectHandler):
    '''
    Renders experiment status
    
    '''
    def initialize(self, db):
        '''
        Init
        
        :param pymongo.MongoClient db: the mongoDB connection
        
        '''
        self._db = db
        
    def get(self, name):
        '''
        GET method
        
        :param str name: workflow name
        
        '''
        rs = self._db[DB_NAME]['experiment'].find({'name': name}).sort('timestamp')
        update_rs = self._db[DB_NAME]['update'].find({'name': name, 'status': 'terminated'}).sort('start_time')
        jobs = set([])
        for d in update_rs:
            #if d['count'] > 10:
            jobs.add({'id': d['job_id'], 'cmdline': self._db[DB_NAME]['cmdline'].find_one({'job_id': d['job_id']})['cmdline']})
        self.render('experiment.html', experiments=[e for e in rs], jobs=jobs)
    
    def post(self, name):
        '''
        POST method
        
        :param str name: workflow name/type
        :raise tornado.web.HTTPError

        '''
        rs = self._db[DB_NAME]['update'].find({
                    'name' : name,
                    'status' : 'terminated'
                }).sort('start_time')
        if rs.count() != 0:
            exp_rs = self._db[DB_NAME]['experiment'].find({'name': name}).sort('timestamp')
            experiments = [e for e in exp_rs]
            data = {
                    'experiments': [e['expid'] for e in experiments],
                    'walltime': [e['walltime'] if 'walltime' in e else 0 for e in experiments],
                    }
            self.set_header('Content-Type', 'application/json;charset="utf-8"')
            self.write(json.dumps(data))
        else:
            self.set_status(404)
        self.finish()
        
class NodeRenderer(tornado.web.RedirectHandler):
    '''
    Renders node listing
    
    '''
    def initialize(self, db):
        '''
        Init
        
        '''
        self._db = db
        
    def get(self, name, expid):
        '''
        GET method
        
        :param str name: workflow name/type
        :param str expid: experiment ID
        
        '''
        rs = self._db[DB_NAME]['experiment'].find_one({
            'name': name,
            'expid': int(expid),
            })
        self.render('node_listing.html', name=name, expid=expid, nodes=rs['nodes'])
        
class NodeStatusRenderer(tornado.web.RedirectHandler):
    '''
    Renders node status
    
    '''
    def initialize(self, db):
        '''
        Init
        
        :param pymongo.MongoClient db: the mongoDB connection
        
        '''
        self._db = db
        
    def get(self, name, expid, nid):
        '''
        GET method
        
        :param str name: workflow name/type
        :param str expid: experiment ID
        :param str nid: node ID
        
        '''
        self.render('node.html')
        
    def post(self, name, expid, nid):
        '''
        POST method
        
        :param str name: workflow name/type
        :param str expid: experiment ID
        :param str nid: node ID
        
        '''
        rs = self._db[DB_NAME]['update'].find({
                    'name' : name,
                    'host' : nid,
                    'expid' : int(expid),
                }).sort('timestamp')
        if rs.count() != 0:
            data = []
            db_data = [d for d in rs]
            for d in db_data:
                del d['_id']
                data.append(d)
            self.set_header('Content-Type', 'application/json;charset="utf-8"')
            self.write(json.dumps(data))
        else:
            self.set_status(404)
        self.finish()
