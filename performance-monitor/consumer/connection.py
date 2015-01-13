'''
Created on Jan 12, 2015

@author: dc
'''
import pika 
from pika import adapters

class MessageConnection(object):
    '''
    An auto-recovery AMQP connection
    
    '''
    
    def __init__(self, amqp):
        '''
        
        '''
        self._params = pika.URLParameters(amqp)
        self._consumers = set([])
        self._closing = False
        self._conn = None
       
    @property
    def is_connected(self):
        '''
        Connection state
        '''
        return self._conn != None 
    
    def connect(self):
        '''
        Establish the AMQP connection
        
        '''
        self._conn = adapters.TornadoConnection(
                parameters=self._params,
                on_close_callback=self._on_close,
                )
        
    def add_consumer(self, c):
        '''
        Add a consumer to the connection
        
        :param message_consumer.MessageConsumer c: message consumer
        
        '''
        self._consumers.add(c)
        
    def remove_consumer(self, c):
        '''
        Remove a consumer from the connection
        
        :param message_consumer.MessageConsumer c: message consumer 
        
        '''
        if c in self._consumers:
            self._consumers.remove(c)
            
    def stop(self):
        '''
        Stop the connection
        
        '''
        self._closing = True
        while self._consumers:
            self._consumers.pop()
        self._conn.close()
        
    def add_timeout(self, period, callback):
        '''
        Wrap-up of pika.connection.Connection.add_timeout
        
        :param int period: timeout period in seconds
        :param method callback: callback function to execute after timeout 
        
        '''
        self._conn.add_timeout(period, callback)
        
    def channel(self, callback):
        '''
        Wrap-up of pika.connection.Connection.channel
        
        :param method callback: callback function to execute after the channel is established successfully 
        
        '''
        self._conn.channel(callback)
        
    def _on_open(self, conn):
        '''
        Callback function to execute after the connection is established successfully
        
        :param pika.connection.Connection conn: the established connection 
        
        '''
        for c in self._consumers:
            conn.channel(c.on_channel_open)
    
    def _on_close(self, conn, code, text):
        '''
        Callback function to execute when the connection is being torn down
        
        :param pika.connection.Connection conn: the connection
        :param int code: the reply code given by the broker
        :param str text: the reply text given by the broker
        
        '''    
        if self._closing:
            self.stop()
        else:
            self._conn.add_timeout(1, self._reconnect)
            
    def _reconnect(self):
        '''
        Re-establish the connection
        '''
        self._conn = adapters.TornadoConnection(
                parameters=self._params,
                on_open_callback=self._on_open,
                on_close_callback=self._on_close,
                )