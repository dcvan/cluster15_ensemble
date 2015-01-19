'''
Created on Jan 13, 2015

@author: dc
'''
import json
import uuid
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
        rs = self._db[DB_NAME]['workflows'].find(fields={'_id': 0}).sort('name')
        self.render('workflows.html', workflows=[w for w in rs])
    
    def post(self):
        '''
        POST method
        
        '''
        data = json.loads(self.request.body)
        data['exp_id'] = str(uuid.uuid4())
        data['status'] = 'submitted'
        self._db[DB_NAME]['experiments'].insert(data)
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
        self.render('experiment.html')

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
