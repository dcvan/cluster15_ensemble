'''
Created on Jan 13, 2015

@author: dc
'''
import json
import tornado.web

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
        self.render('experiment.html')
    
    def post(self, name):
        '''
        POST method
        
        :param str name: workflow name/type
        :raise tornado.web.HTTPError

        '''
        rs = self._db['cluster15']['experiment'].find({
                    'name' : name,
                    'status' : 'terminated'
                }).sort('timestamp')
        if rs:
            data = []
            for d in rs:
                del d['_id']
                data.append(d)
            self.set_header('Content-Type', 'application/json;charset="utf-8"')
            self.write(json.dumps(data))
            self.finish()
        else:
            raise tornado.web.HTTPError(404)
    
class WorkerStatusRenderer(tornado.web.RedirectHandler):
    '''
    Renders worker status
    
    '''
    def initialize(self, db):
        '''
        Init
        
        :param pymongo.MongoClient db: the mongoDB connection
        
        '''
        self._db = db
        
    def get(self, name, expid, wid):
        '''
        GET method
        
        :param str name: workflow name/type
        :param str expid: experiment ID
        :param str wid: worker ID
        :raise tornado.web.HTTPError
        
        '''
        self.render('worker.html')
        
    def post(self, name, expid, wid):
        '''
        POST method
        
        :param str name: workflow name/type
        :param str expid: experiment ID
        :param str wid: worker ID
        :raise tornado.web.HTTPError
        
        '''
        rs = self._db['cluster15']['experiment'].find({
                    'name' : name,
                    'host' : 'condor-%s' % wid,
                    'expid' : int(expid),
                }).sort('timestamp')
        if rs:
            data = []
            for d in rs:
                del d['_id']
                data.append(d)
            self.set_header('Content-Type', 'application/json;charset="utf-8"')
            self.write(json.dumps(data))
            self.finish()
        else:
            raise tornado.web.HTTPError(404)
