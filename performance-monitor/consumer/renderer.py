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
        GET method
        
        :param str name: workflow name/type
        :param str expid: experiment ID
        :param str wid: worker ID
        :raise tornado.web.HTTPError
        
        '''
#         if name in self._db.database_names():
#             if expid in self._db[name].collection_names():
#                 rs = self._db[name][expid].find({'host' : 'condor-%s' % wid}).sort('timestamp')
#                 if rs:
#                     self.render("worker.html", 
#                                 labels=[r['executable'] if r['status'] == 'terminated' else '' for r in rs],
#                                 nums=[r['avg_cpu_percent'] if r['status'] == 'terminated' else r['cpu_percent'] for r in rs]
#                                 )
#                 else:
#                     raise tornado.web.HTTPError(404)
#             else:
#                 raise tornado.web.HTTPError(404)
#         else:
#             raise tornado.web.HTTPError(404)
        self.render('worker.html')
        
    def post(self, name, expid, wid):
        '''
        POST method
        
        :param str name: workflow name/type
        :param str expid: experiment ID
        :param str wid: worker ID
        :raise tornado.web.HTTPError
        
        '''
        if name in self._db.database_names():
            if expid in self._db[name].collection_names():
                rs = self._db[name][expid].find({'host' : 'condor-%s' % wid}).sort('timestamp')
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
            else:
                raise tornado.web.HTTPError(404)
        else:
            raise tornado.web.HTTPError(404)