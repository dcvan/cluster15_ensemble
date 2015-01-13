'''
Created on Jan 13, 2015

@author: dc
'''
import json
import tornado.web

class WorkerStatusRenderer(tornado.web.RedirectHandler):
    '''
    A web handler that renders status page of the worker of interest
    
    '''

    def initialize(self, db):
        '''
        Initialize the handler
        
        :param pymongo.MongoClient db: the mongoDB connection
        
        '''
        self._db = db
        
    def get(self, name, expid, wid):
        '''
        
        '''
        self.render("worker.html")
        
    def post(self, name, expid, wid):
        '''
        
        '''
        if name in self._db.database_names():
            if expid in self._db[name].collection_names():
                rs = self._db[name][expid].find({'host' : 'condor-%s' % wid})
                if rs:
                    data = [d for d in rs]
                    self.set_header('Content-Type', 'application/json;charset="utf-8"')
                    self.write(json.dump(data))
                    self.finish()
                else:
                    raise tornado.web.HTTPError(404)
            else:
                raise tornado.web.HTTPError(404)
        else:
            raise tornado.web.HTTPError(404)
