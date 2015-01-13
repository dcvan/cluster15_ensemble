'''
Created on Jan 12, 2015

@author: dc
'''

import tornado.web
import tornado.ioloop 

from connection import MessageConnection
from update import UpdateHandler
from config import MESSAGE_BROKER_URI

class Application(tornado.web.Application):
    '''
    Tornado server application
    
    '''
    
    def __init__(self):
        '''
        '''
        amqp_conn = MessageConnection(MESSAGE_BROKER_URI)
        handlers = [
                (r'/updates', UpdateHandler, dict(conn=amqp_conn)),   
                ]
        settings = {
                'template_path': 'templates/',
            }
        tornado.web.Application.__init__(self, handlers, **settings)
    

if __name__ == '__main__':
    try:
        app = Application()
        app.listen(8081)
        print 'Server is running ...'
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.current().stop()
