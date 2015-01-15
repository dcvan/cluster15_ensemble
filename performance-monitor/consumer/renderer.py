'''
Created on Jan 13, 2015

@author: dc
'''
import json
import tornado.web
from config import DB_NAME

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
        self.render('experiment.html', experiments=[e for e in rs])
    
    def post(self, name):
        '''
        POST method
        
        :param str name: workflow name/type
        :raise tornado.web.HTTPError

        '''
        rs = self._db[DB_NAME]['update'].find({
                    'name' : name,
                    'status' : 'terminated'
                }).sort('timestamp')
        if rs.count() != 0:
            experiments = self._db[DB_NAME]['experiment'].find({'name': name}).sort('timestamp')
            data = {
                    'experiments': [e['expid'] for e in experiments],
                    'updates': [],
                    }
            for d in rs:
                del d['_id']
                data['updates'].append(d)
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
            for d in rs:
                del d['_id']
                data.append(d)
            self.set_header('Content-Type', 'application/json;charset="utf-8"')
            self.write(json.dumps(data))
        else:
            self.set_status(404)
        self.finish()
