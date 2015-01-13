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
        Allow access from anywhere(test)
    
        '''
        return True
    
    def open(self, name, expid, wid, status):
        '''
        Get/create a WebConsumer to listen to updates of interest when the 
        connection is established
        
        :param str name: workflow name/type
        :param str expid: experiment ID
        :param str wid: worker ID
        :param str status: job status of interest(running/terminated)
        '''
        self._get_consumer(self, '%s.%s.%s.%s' % (name, expid, wid, status, ))
        
    
    def on_close(self):
        '''
        Clean up
        
        '''
        fs = self.request.uri.split('/')
        cid = '.'.join((fs[2], fs[4], fs[6], fs[7], ))
        self._consumers[cid].remove(self)
        self._conn.remove_consumer(self._consumers[cid])

        
    def _get_consumer(self, listener, topic):
        '''
        Get an existing consumer or creating a new one to consume messages
        
        :param tornado.websocket.WebSocketHandler listener: the event handler
        :param str name: the target experiment name
        
        '''
        def callback():
            c = message_consumer.WebConsumer(topic)
            c.add_listener(listener)
            self._conn.channel(c.on_channel_open)
            self._conn.add_consumer(c)
            self._consumers[topic] = c
            
            
        if not self._conn.is_connected:
            self._conn.connect()
            self._conn.add_timeout(1, callback)
        elif topic not in self._consumers:
            self._conn.add_timeout(1, callback)
        else:
            self._consumers[topic].add_listener(listener)
    
        