'''
Created on Jan 12, 2015

@author: dc
'''

import tornado.web
import tornado.ioloop 
import pymongo

from message_consumer import ArchiveConsumer
from connection import MessageConnection
from message import UpdateHandler
from renderer import ExperimentStatusRenderer, NodeRenderer, NodeStatusRenderer
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
                # experiments
                (r'/types/([a-z-]+)', ExperimentStatusRenderer, dict(db=self._mongo_conn)),
                # nodes
                (r'/types/([a-z-]+)/experiments/([0-9]+)', NodeRenderer, dict(db=self._mongo_conn)),
                # node
                (r'/types/([a-z-]+)/experiments/([0-9]+)/nodes/([a-z0-9]+)', NodeStatusRenderer, dict(db=self._mongo_conn)),
                (r'/types/([a-z-]+)/experiments/([0-9]+)/nodes/([0-9]+)/([a-z#]+)', UpdateHandler, dict(conn=self._amqp_conn, consumers={})),
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
