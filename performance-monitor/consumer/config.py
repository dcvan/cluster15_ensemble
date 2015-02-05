'''
Created on Jan 13, 2015

@author: dc
'''

MESSAGE_BROKER_URI = 'amqp://dc:cluster15@152.54.14.32:5672/%2F'

EXCHANGE_NAME = 'cluster15_stat'

ARCHIVE_HOST = '127.0.0.1'

ARCHIVE_PORT = 27017

DB_NAME = 'cluster15'

DATA_LEN_LIMIT = 300

def check_content_type(handler):
    '''
    
    '''
    content_type = handler.request.headers.get('Content-Type')
    if content_type and content_type not in ['application/json', 'application/x-www-form-urlencoded']:
        handler.set_status(415, 'Unsupported content-type')
        return None
    if not content_type:
        content_type = 'text/html'
    return content_type
