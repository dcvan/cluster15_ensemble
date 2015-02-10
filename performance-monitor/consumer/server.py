'''
Created on Jan 12, 2015

@author: dc
'''
import pymongo
import tornado.web
import tornado.ioloop 

from message_consumer import ArchiveConsumer
from connection import MessageConnection
from renderer import *
from config import MESSAGE_BROKER_URI, ARCHIVE_HOST, ARCHIVE_PORT

class Application(tornado.web.Application):
    '''
    Tornado server application
    
    '''
    
    def __init__(self):
        '''
        
        '''
        self._amqp_conn = MessageConnection(MESSAGE_BROKER_URI)
        self._mongo_conn = pymongo.MongoClient(ARCHIVE_HOST, ARCHIVE_PORT)
        self._start_archive_consumer()
        handlers = [
                  (r'/', WorkflowsRenderer, dict(db=self._mongo_conn)),
                  (r'/deployments/([a-z-]+)', DeploymentRender, dict(db=self._mongo_conn)),
                  (r'/workflows/([a-z-_]+)', WorkflowRenderer,  dict(db=self._mongo_conn)),
                  (r'/workflows/([a-z-_]+)/analysis', AnalysisRenderer, dict(db=self._mongo_conn)),
                  (r'/workflows/([a-z-_]+)/experiments/([a-z0-9-]+)', ExperimentRenderer, dict(db=self._mongo_conn)),
                  (r'/workflows/([a-z-_]+)/experiments/([a-z0-9-]+)/manifest', ManifestRenderer, dict(db=self._mongo_conn)),
                  (r'/workflows/([a-z-_]+)/experiments/([a-z0-9-]+)/runs', RunsRenderer, dict(db=self._mongo_conn)),
#                   (r'/workflows/([a-z-_]+)/experiments/([a-z0-9-]+)/workers/([a-z0-9-]+)', WorkerRenderer, dict(db=self._mongo_conn)),
                  (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
                  (r'/tmp/(.*)', tornado.web.StaticFileHandler, {'path': '/tmp/'}),
                  (r'/pdf/(.*)', PDFRenderer),
                ]
        settings = {
                'template_path': 'templates/',
                'static_path': 'static/'
            }
        tornado.web.Application.__init__(self, handlers, **settings)
        
    def stop(self):
        '''
        Clean up
        
        '''
        if self._amqp_conn:
            self._amqp_conn.stop()
        if self._mongo_conn and self._mongo_conn.alive():
            self._mongo_conn.close()
        
    def _start_archive_consumer(self):
        '''
        Start archive consumer
        
        '''
        def callback():
            c = ArchiveConsumer(self._mongo_conn)
            self._amqp_conn.channel(c.on_channel_open)
            self._amqp_conn.add_consumer(c)
        if not self._amqp_conn.is_connected:
            self._amqp_conn.connect()
        self._amqp_conn.add_timeout(1, callback)

if __name__ == '__main__':
    try:
        app = Application()
        app.listen(8081)
        print 'Server is running ...'
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        app.stop()
        tornado.ioloop.IOLoop.current().stop()
