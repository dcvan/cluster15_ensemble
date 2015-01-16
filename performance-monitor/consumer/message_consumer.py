'''
Created on Jan 12, 2015

@author: dc
'''
import json

from config import EXCHANGE_NAME, DB_NAME

class MessageConsumer(object):
    '''
    General message consumer. Usually not instantiated
    
    '''

    def __init__(self, topic=''):
        '''
        
        '''
        self._topic = topic 
        self._queue = ''
        self._ch = None
        self._consumer_tag = None
        self._last_timestamp = 0
        
    def on_channel_open(self, ch):
        '''
        Declare the exchange when the channel is opened
        
        :param pika.channel.Channel ch: the opened channel
        
        '''
        self._ch = ch
        self._ch.add_on_cancel_callback(self._on_channel_cancelled)
        self._ch.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type='topic',
                durable=True,
                callback=self._on_exchange_declareok,
            )

    def stop(self):
        '''
        Stop a consumer
        
        '''
        self._ch.basic_cancel(consumer_tag=self._consumer_tag)
        self._ch.close()
        
    def _on_channel_cancelled(self, ch):
        '''
        Close the channel when the channel is being cancelled
        deliver
        '''
        if self._ch:
            self._ch.close()
    
    def _on_exchange_declareok(self, method):
        '''
        Declare a queue when the exchange is declared OK
        
        :param pika.frame.Method method: unused
        
        '''
        self._ch.queue_declare(
                exclusive=True,
                callback=self._on_queue_declareok,
                )
        
    def _on_queue_declareok(self, method):
        '''
        Bind the queue and the exchange when the queueu is declared OK
        
        :param pika.frame.Method method: the frame with queue name given by the broker
        
        '''
        self._queue = method.method.queue
        self._ch.queue_bind(
                 exchange=EXCHANGE_NAME,
                 queue=self._queue,
                 routing_key=self._topic, 
                 callback=self._on_bindok,
                 )
        
    def _on_bindok(self, method):
        '''
        Start consuming 
        
        :param pika.frame.Method method: unused
    
        '''
        self._consumer_tag = self._ch.basic_consume(
                queue=self._queue,
                consumer_callback=self._on_message, 
                )
        
    def _on_message(self, ch, deliver, prop, body):
        '''
        Consume and ack messages
        
        :param pika.channel.Channel ch: the channel
        :param pika.Spec.Basic.Deliver: frame contains delivery tag
        :param pika.Spec.BasicProperties: frame contains user-define properties
        :param str body: message text body    
        
        '''
        timestamp = int(prop.timestamp)
        if timestamp > self._last_timestamp:
            if body == 'stopping':
                self._ch.basic_ack(deliver.delivery_tag)
                self.stop()
            else:
                self.process(deliver, prop, body)
                self._last_timestamp = timestamp
                self._ch.basic_ack(deliver.delivery_tag)
            
    def process(self, deliver, prop, body):
        '''
        Implemented by subclasses
        
        :param str body: message text body   
        :param pika.Spec.Basic.Deliver: frame contains delivery tag
        :param pika.Spec.BasicProperties: frame contains user-define properties
        :raise NotImplementedError
        
        '''
        
        raise NotImplementedError

class WebConsumer(MessageConsumer):
    '''
    Message consumer for real-time message notification
    
    '''
    def __init__(self, topic):
        '''
    
        '''
        super(WebConsumer, self).__init__(topic)
        self._listeners = set([])
        
    def add_listener(self, l):
        '''
        Add listener
        
        '''
        self._listeners.add(l)
        
    def remove_listener(self, l):
        '''
        Remove listener
        
        '''
        self._listeners.remove(l)
        
    def _on_queue_declareok(self, method):
        '''
        Add "stopping" routing key to the binding so that the consumer can 
        detect if the corresponding producer is stopped
        
        :param pika.frame.Method method: the frame with queue name given by the broker
        
        '''
        self._queue = method.method.queue
        super(WebConsumer, self)._on_queue_declareok(method)
        
    def process(self, deliver, prop, body):
        '''
        Write messages to listeners
        
        :param pika.Spec.Basic.Deliver: frame contains delivery tag
        :param pika.Spec.BasicProperties: frame contains user-define properties
        :param str body: message text body
        
        '''
        for l in self._listeners:
            l.write_message(body)
        
        data = json.loads(body)
        if 'status' in data and data['status'] =='finished':
            self._ch.basic_ack(deliver.delivery_tag)
            self.stop()
                
                 
class ArchiveConsumer(MessageConsumer):
    '''
    Message consumer for message persistence
    
    '''
    
    def __init__(self, db):
        '''
        
        :param pymongo.MongoClient db: mongoDB connection
        
        '''
        super(ArchiveConsumer, self).__init__('#')
        self._db = db
    
    def stop(self):
        '''
        Close DB connection when stopping the consumer
        
        '''
        self._db.close()
        super(ArchiveConsumer, self).stop()
        
    def process(self, deliver, prop, body):
        '''
        Store message into DB
        
        :param pika.Spec.Basic.Deliver: frame contains delivery tag
        :param pika.Spec.BasicProperties: frame contains user-define properties
        :param str body: message text body   
       
        '''
        data = json.loads(body)
        if 'status' in data:
            if data['status'] == 'nascent':
                data['status'] = 'running'
                if 'workflow' not in self._db[DB_NAME].collection_names() or self._db[DB_NAME]['workflow'].find({'name': data['name']}).count() == 0:
                    self._db[DB_NAME]['workflow'].insert({
                            'name': data['name'],
                            'timestamp': data['timestamp']
                            })
                if 'experiment' not in self._db[DB_NAME].collection_names():
                    data['nodes'] = []
                    data['nodes'].append(data['hostname'])
                    del data['hostname']
                    self._db[DB_NAME]['experiment'].insert(data)
                elif self._db[DB_NAME]['experiment'].find({'expid': data['expid']}).count() == 0:
                    data['nodes'] = []
                    data['nodes'].append(data['hostname'])
                    del data['hostname']
                    self._db[DB_NAME]['experiment'].insert(data)
                else:
                    self._db[DB_NAME]['experiment'].update({'expid': data['expid']}, {'$addToSet': {'nodes': data['hostname'], 'timestamp': data['timestamp']}})
            elif data['status'] == 'finished':
                if data['walltime']:
                    self._db[DB_NAME]['experiment'].update({'expid': data['expid']}, {'$set': data}, upsert=True)
            else:
                if data['status'] == 'terminated':
                    if data['count'] <= 1:
                        self._db[DB_NAME]['update'].remove({'expid': data['expid'], 'start_time': data['start_time']})
                        return 
                self._db[DB_NAME]['update'].insert(data)
        else:
            # garbled message
            pass
        