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
                'topology': [t for t in self._db[DB_NAME]['topology'].find({}, {'_id': 0})],
                'mode': [m for m in self._db[DB_NAME]['mode'].find({}, {'_id': 0})],
                'worker_size': [w for w in self._db[DB_NAME]['vm_size'].find({}, {'_id': 0})],
                'storage_site': [ss for ss in self._db[DB_NAME]['storage_site'].find({}, {'_id': 0})],
                'storage_type': [st for st in self._db[DB_NAME]['storage_type'].find({}, {'_id': 0})],
            }
        self.render('workflows.html', workflows=[w for w in self._db[DB_NAME]['workflow'].find({}, {'_id': 0}).sort('name')], data=data)
    
    def post(self):
        '''
        POST method
        
        '''
        data = json.loads(self.request.body)
        data['exp_id'] = str(uuid.uuid4())
        data['status'] = 'submitted'
        data['create_time'] = int(time.time())
        self._db[DB_NAME]['experiment'].insert(data)
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
        GET method
        
        '''
        exp = self._db[DB_NAME]['experiment'].find_one({'exp_id': exp_id}, {'_id': 0})
        template = self._db[DB_NAME]['manifest'].find_one({
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
        exp['resource_type'] = 'BareMetalCE'  if exp['worker_size'] == 'ExoGENI-M4' else 'VM'
        exp['executables'] = self._db[DB_NAME]['workflow'].find_one({'name': workflow}, {'_id': 0})['executables']
        manifest = jinja2.Template(template).render(param=exp)
        exp['worker_size'] = self._db[DB_NAME]['vm_size'].find_one({'value': exp['worker_size']}, {'_id': 0})['name']
        exp['create_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp['create_time']))
        if exp['bandwidth']: exp['bandwidth'] /= (1000 * 1000)
        self.render('experiment.html', manifest=manifest, data=exp)

    def post(self, workflow, exp_id):
        '''
        POST method
        '''
        exp = self._db[DB_NAME]['experiment'].find_one({'exp_id': exp_id}, {'_id': 0})
        template = self._db[DB_NAME]['manifest'].find_one({
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
        exp['executables'] = self._db[DB_NAME]['workflow'].find_one({'name': workflow}, {'_id': 0})['executables']
        manifest = jinja2.Template(template).render(param=exp)
        self.set_header('Content-Type', 'application/rdf+xml')
        self.set_header('Content-Disposition', 'attachment;filename=%s' % '-'.join([exp['type'], exp['topology'], exp['mode']]))
        self.write(manifest)
        
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
