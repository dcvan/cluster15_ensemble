'''
Created on Jan 12, 2015

@author: dc
'''

import pika
import json
import time
from pika import adapters
from multiprocessing import Process
from config import EXCHANGE_NAME, RECONNECT_INT

class MessageSender(Process):
    '''
    Send performance messages to the message queue
    
    '''

    def __init__(self, expid, conn_param, msg_q, hostname):
        '''
        
        :param int expid: experiment ID
        :param pika.connection.ConnectionParameters conn_param: AMQP connection parameters
        :param multiprocessing.Queue: system message queue for communication between the monitor
                                      and the AMQP sender
        :param str hostname: the hostname
        
        '''
        Process.__init__(self)
        self._conn_param = conn_param
        self._msg_q = msg_q
        self._conn = None
        self._ch = None
        self._queue = None
        self._closing = False
        self._stopping = False
        self._expid = expid
        self._hostname = hostname

    
    @property
    def name(self):
        return 'MessageSender'
    
    def run(self):
        '''
        Override run()
        
        '''
        try:
            self._start()
        except KeyboardInterrupt:
            pass
        
    def _start(self):
        '''
        Start sender
        
        '''
        self._conn = self._connect()
        self._conn.ioloop.start()
        
    def stop(self):
        '''
        Stop sender
        
        '''
        if not self._conn:
            return
        self._stopping = True
        if self._ch:
            self._ch.close()
        self._closing = True
        self._conn.close()
        self._msg_q.close()
        
    def _connect(self):
        '''
        Establish a connection to the message broker
        
        :rtype pika.connection.Connection
        
        '''
        return adapters.TornadoConnection(self._conn_param, self._on_connection_open)
    
    def _reconnect(self):
        '''
        Reconnect to the message broker 
        
        '''
        if not self._closing:
            self._conn = self._connect()
            
    def _on_connection_open(self, conn):
        '''
        Create the channel when the connection is established
        
        :param pika.connection.Connection conn: the established connection
        
        '''
        self._conn.add_on_close_callback(self._on_connection_closed)
        self._conn.channel(self._on_channel_open)
        
    def _on_connection_closed(self, conn, reply_code, reply_text):
        '''
        Reconnect if the connection is closed unexpectedly or close the connection if it is intended
        
        :param pika.connection.Connection conn: the connection 
        :param int reply_code: the reply code given by the broker
        :param str reply_text: the reply text given by the broker
        
        '''
        if self._closing:
            self._conn.ioloop.stop()
        else:
            self._conn.add_timeout(RECONNECT_INT, self._reconnect)
            
    def _on_channel_open(self, ch):
        '''
        Declare the permanent exchange when the channel is open. 
        
        :param pika.channel.Channel ch: the channel
        
        '''
        self._ch = ch
        self._ch.add_on_close_callback(self._on_channel_closed)
        self._ch.exchange_declare(
                 exchange=EXCHANGE_NAME,
                 exchange_type='topic',
                 durable=True,
                 callback=self._on_exchange_declareok,
                 )
        
    def _on_channel_closed(self, ch, reply_code, reply_text):
        '''
        Close the connection if it is marked as closed
        
        :param pika.channel.Channel ch: the opened channel
        :param int reply_code: reply code returned by the broker
        :param str reply_text: reply text returned by the broker
        
        '''
        self._conn.close()
        
    def _on_exchange_declareok(self, method):
        '''
        Declare a temporary queue when the exchange is declared OK
        
        :param pika.frame.Method method: unused
        
        '''
        self._publish()
        
    def _on_queue_declareok(self, method):
        '''
        Get the queue name and bind the queue with the exchange
        
        :param pika.frame.Method method: the frame with queue name given by the broker
        
        '''
        self._queue = method.method.queue 
        self._ch.queue_bind(
                exchange=EXCHANGE_NAME,
                queue=self._queue,
                routing_key='#',
                callback=self._on_bindok,
                )
        
    def _on_bindok(self, method):
        '''
        Preparing for publishing messages when the binding is successful
        
        :param pika.frame.Method method: unused 
        
        '''
#        self._ch.confirm_delivery(self._on_delivery_confirmed)
        self._publish()

    def _publish(self):
        '''
        Publish performance data messages
        
        :raise Queue.Empty
        
        '''
        if self._stopping:
            return
        msg = self._msg_q.get(True)
        if  msg:
            topics = '%s.%s.%s' % (self._expid, self._hostname, msg['type'])
            del msg['type']
            self._ch.basic_publish(
                     exchange=EXCHANGE_NAME, 
                     routing_key=topics,
                     body=json.dumps(msg),
                     properties=pika.BasicProperties(
                        delivery_mode=2,
                        timestamp=int(time.time() * 1000)),
                     )
        
        if msg:
            self._conn.add_timeout(1, self._publish)
        else:
            self.stop()
        
