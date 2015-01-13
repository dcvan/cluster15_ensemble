'''
Created on Jan 12, 2015

@author: dc
'''

import tornado.websocket
import message_consumer

class UpdateHandler(tornado.websocket.WebSocketHandler):
    '''
    A WebSocket event handler to update performance stats at real-time
    
    '''
    
    def initialize(self, conn, consumers):
        '''
        Initialize the event handler
        
        :param pika.connection.Connection conn: the AMQP connection
        :param dict consumers: consumers
        '''
        self._conn = conn
        self._consumers = consumers
        
    def check_origin(self, origin):
        '''
    
        '''
        return True
    
    def open(self):
        '''
        
        '''
        self._get_consumer(self, 'test')
    
    def _get_consumer(self, listener, name):
        '''
        Get an existing consumer or creating a new one to consume messages
        
        :param tornado.websocket.WebSocketHandler listener: the event handler
        :param str name: the target experiment name
        
        '''
        def callback():
            c = message_consumer.WebConsumer('%s.#' % name)
            c.add_listener(listener)
            self._conn.channel(c.on_channel_open)
            self._conn.add_consumer(c)
            self._consumers[name] = c
            
            
        if not self._conn.is_connected:
            self._conn.connect()
            self._conn.add_timeout(1, callback)
        elif name not in self._consumers:
            self._conn.add_timeout(1, callback)
        else:
            self._consumers[name].add_listener(listener)
    
        