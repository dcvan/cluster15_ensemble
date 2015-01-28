'''
Created on Jan 13, 2015

@author: dc
'''
import json
import uuid
import jinja2
import time
import math
import tornado.web
from config import DB_NAME, check_content_type

class WorkflowsRenderer(tornado.web.RedirectHandler):
    '''
    Renders worklow listing
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
    
    def get(self):
        '''
        GET method
        
        '''
        data = {
                'topology': [t for t in self._db[DB_NAME]['workflow']['topology'].find(fields={'_id': 0})],
                'mode': [m for m in self._db[DB_NAME]['workflow']['mode'].find(fields={'_id': 0})],
                'site': [s for s in self._db[DB_NAME]['workflow']['site'].find(fields={'_id': 0})],
                'worker_size': [w for w in self._db[DB_NAME]['workflow']['vm_size'].find(fields={'_id': 0})],
                'storage_site': [ss for ss in self._db[DB_NAME]['workflow']['storage_site'].find(fields={'_id': 0})],
                'storage_type': [st for st in self._db[DB_NAME]['workflow']['storage_type'].find(fields={'_id': 0})],
            }
        self.render('workflows.html', workflows=[w for w in self._db[DB_NAME]['workflow']['type'].find({}, {'_id': 0}).sort('name')], data=data)
    
    def post(self):
        '''
        POST method: create new experiment
        
        '''
        content_type = check_content_type(self)
        if not content_type:
            return
        data = json.loads(self.request.body)
        if not self._db[DB_NAME]['workflow']['manifest'].find_one({
                'type': data['type'],
                'mode': data['mode'],
                'storage_site': data['storage_site'],
                'storage_type': data['storage_type'],
            }):
            self.set_status(404, 'Manifest not available yet')
            return
        data['exp_id'] = str(uuid.uuid4())
        data['status'] = 'submitted'
        data['create_time'] = int(time.time())
        self._db[DB_NAME]['workflow']['experiment'].insert(data)
        if content_type == 'application/json':
            self.write({
                    'exp_id': data['exp_id'],
                    'type': data['type'],
                })
        
class ExperimentRenderer(tornado.web.RedirectHandler):
    '''
    Renders specific experiment info
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
    
    def get(self, workflow, exp_id):
        '''
        GET method: renders experiment page
        
        '''
        exp = self._db[DB_NAME]['workflow']['experiment'].find_one({'exp_id': exp_id}, {'_id': 0})
        if not exp:
            self.set_status(404, 'Experiment not found')
            return 
        content_type = check_content_type(self)
        if not content_type:
            return
        if content_type == 'text/html':
            manifest = self._get_manifest(workflow, exp)
            exp['worker_size'] = self._db[DB_NAME]['workflow']['vm_size'].find_one({'value': exp['worker_size']}, {'_id': 0})['name']
            exp['create_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp['create_time']))
            exp['workers'] = [w for w in self._db[DB_NAME]['experiment']['worker'].find({'exp_id': exp_id}, {'_id': 0}).sort('host')]
            exp['runs'] = [r for r in self._db[DB_NAME]['experiment']['run'].find({'exp_id': exp_id}, {'_id': 0}).sort('run_id')]
            if exp['bandwidth']: exp['bandwidth'] /= (1000 * 1000)
            self.render('experiment.html', manifest=manifest, data=exp, current_uri=self.request.uri)
        elif content_type == 'application/json':
            del exp['create_time']
            del exp['exp_id']
            del exp['status']
            self.write(exp)
            
    def post(self, workflow, exp_id):
        '''
        POST method: provides manifest download
        
        '''
        exp = self._db[DB_NAME]['workflow']['experiment'].find_one({'exp_id': exp_id}, {'_id': 0})
        if not exp:
            self.set_status(404, 'Experiment not found')
            return 
       
        self.set_header('Content-Type', 'application/rdf+xml')
        self.set_header('Content-Disposition', 'attachment;filename=%s' % '-'.join([exp['type'], exp['topology'], exp['mode'], exp['worker_size'], exp['master_site']]))
        self.write(self._get_manifest(workflow, exp))
        
    def delete(self, workflow, exp_id):
        '''
        DELETE method: delete an experiment
        
        '''
        content_type = check_content_type(self)
        if not content_type:
            return
        if not self.request.body:
            self.set_status(400, 'No action specified')
            return 
        param = json.loads(self.request.body)
        if param['action'] not in set(['remove', 'redo']):
            self.set_status(400, 'Unknown action')
            return 
        if param['action'] == 'remove':
            self._db[DB_NAME]['workflow']['experiment'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['worker'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['job'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['system'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['run'].remove({'exp_id': exp_id})
        
    def _get_manifest(self, workflow, exp):
        '''
        '''
        exp['image'] = self._db[DB_NAME]['workflow']['image'].find_one({'name': workflow})
        t = self._db[DB_NAME]['workflow']['manifest'].find_one({
                    'type': exp['type'],
                    'mode': exp['mode'],
                    'storage_site': exp['storage_site'],
                    'storage_type': exp['storage_type'],
                    }, {'_id': 0, 'master_postscript': 1, 'worker_postscript': 1})
        if not t:
            self.set_status(404, 'Manifest not available yet')
            return
        if exp['mode'] == 'multinode' and not exp['bandwidth']:
            exp['bandwidth'] = 500000000
        if exp['storage_site'] == 'remote' and not exp['storage_size']:
            exp['storage_size'] = 50
        exp['resource_type'] = 'BareMetalCE' if exp['worker_size'] == 'ExoGENI-M4' else 'VM'
        exp['executables'] = self._db[DB_NAME]['workflow']['type'].find_one({'name': workflow}, {'_id': 0})['executables']
        exp['master_postscript'] = jinja2.Template(t['master_postscript']).render(param={
                                                                                        'exp_id': exp['exp_id'],
                                                                                        'site': exp['master_site'],
                                                                                        'executables': exp['executables'],
                                                                                        'worker_num': 1 if exp['mode'] == 'standalone' else sum([int(s['num']) for s in exp['worker_sites']]),
                                                                                        'run_num': exp['run_num']
                                                                                            })
        if 'worker_postscript' in t:
            for w in exp['worker_sites']:
                w['worker_postscript'] = jinja2.Template(t['worker_postscript']).render(param={
                                                                                            'exp_id': exp['exp_id'],
                                                                                            'site': w['site'],
                                                                                            'executables': exp['executables']   
                                                                                            })
        if 'worker_sites' in exp:
            for w in exp['worker_sites']:
                w['num'] = int(w['num'])
        mantemp = self._db[DB_NAME]['workflow']['template'].find_one({'name': 'manifest'})['value']
        return jinja2.Template(mantemp).render(param=exp)
        
class RunsRenderer(tornado.web.RedirectHandler):
    '''
    Renders runs
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
        
    def post(self, workflow, exp_id):
        '''
        POST method: get run related info
        
        '''
        if not self._db[DB_NAME]['workflow']['experiment'].find({'exp_id': exp_id}).count():
            self.set_status(404, 'Experiment not found')
        runs = [r for r in self._db[DB_NAME]['experiment']['run'].find({'exp_id': exp_id}, {'_id': 0})]
        if not runs:
            self.set_status(204, 'No finished runs')
            return
        self.write({
                'label': [r['run_id'] for r in runs],
                'walltime': [r['walltime'] for r in runs]
            })
        
class WorkerRenderer(tornado.web.RedirectHandler):
    '''
    Renders worker specific info
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
        
    def get(self, workflow, exp_id, worker):
        '''
        GET method: renders worker page
        
        '''
        if not self._db[DB_NAME]['experiment']['worker'].find({'exp_id': exp_id}).count():
            self.set_status(404, 'Experiment or worker not found')
            return
        self.render('worker.html', worker=worker)
    
    def post(self, workflow, exp_id, worker):
        '''
        POST method: returns performance data
        
        '''
        content_type = check_content_type(self)
        if not content_type:
            return
        data = json.loads(self.request.body)
        if not self._db[DB_NAME]['workflow']['experiment'].find().count():
            self.set_status(404, 'Experiment not found')
            return
        if not data or 'aspect' not in data:
            self.set_status(422, 'No query identified')
            return
        if data['aspect'] != 'system' and data['aspect'] != 'job':
            self.set_status(422, 'Unknown query')
            return
        stat = [s for s in self._db[DB_NAME]['experiment'][data['aspect']].find({'exp_id': exp_id, 'host': worker}, {'_id': 0}).sort('timestamp')]
        if not stat or len(stat) < 2:
            self.set_status(204, 'Data not available yet')
            return
        res = {}
        if data['aspect'] == 'system':
            res['label'] = [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s['timestamp'])) for s in stat ]
            res['sys_cpu_percent'] = [s['sys_cpu_percent'] for s in stat]
            res['sys_max_cpu_percent'] = [s['sys_max_cpu_percent'] for s in stat]
            res['sys_min_cpu_percent'] = [s['sys_min_cpu_percent'] for s in stat]
            res['sys_max_mem_percent'] = [s['sys_max_mem_percent'] for s in stat]
            res['sys_min_mem_percent'] = [s['sys_min_mem_percent'] for s in stat]
            res['sys_mem_percent'] = [s['sys_mem_percent'] for s in stat]
            res['sys_read_rate'] = [s['sys_read_rate'] for s in stat]
            res['sys_write_rate'] = [s['sys_write_rate'] for s in stat]
            res['sys_send_rate'] = [s['sys_send_rate'] for s in stat]
            res['sys_recv_rate'] = [s['sys_recv_rate'] for s in stat]
        else:
            res['label'] = [s['cmdline'] for s in stat]
            res['avg_cpu_percent'] = [s['avg_cpu_percent'] for s in stat]
            res['max_cpu_percent'] = [s['max_cpu_percent'] for s in stat]
            res['min_cpu_percent'] = [s['min_cpu_percent'] for s in stat]
            res['max_mem_percent'] = [s['max_mem_percent'] for s in stat]
            res['min_mem_percent'] = [s['min_mem_percent'] for s in stat]
            res['avg_mem_percent'] = [s['avg_mem_percent'] for s in stat]
            res['runtime'] = [s['runtime'] for s in stat]
            res['read_rate'] = [s['total_read_bytes'] / s['runtime'] for s in stat]
            res['write_rate'] = [s['total_write_bytes'] / s['runtime'] for s in stat]
            res['total_read_bytes'] = [s['total_read_bytes'] for s in stat]
            res['total_write_bytes'] = [s['total_write_bytes'] for s in stat]
        if content_type == 'application/json':
            self.write(res)
        
class WorkflowRenderer(tornado.web.RequestHandler):
    '''
    Renders experiment listing
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        :param pymongo.MongoClient db: the MongoDB connection
        
        '''
        self._db = db
        
    def get(self, workflow):
        '''
        GET method: renders experiments listing page
        
        '''
        # check workflow availability
        workflow_exist = self._db[DB_NAME]['workflow']['type'].find_one({'name': workflow}, {'_id': 0})
        if not workflow_exist:
            self.set_status(404, 'Workflow not available')
            return 
        
        # check MIME type support
        content_type = check_content_type(self)
        if not content_type:
            return
        
        # get arguments
        query = {'type': workflow}
        if self.get_arguments('worker_size'):
            query['worker_size'] = self.get_arguments('worker_size')[0]
        if self.get_arguments('mode'):
            query['mode'] = self.get_arguments('mode')[0]
        if self.get_arguments('topology'):
            query['topology'] = self.get_arguments('topology')[0]
        if self.get_arguments('master_site'):
            query['master_site'] = self.get_arguments('master_site')[0]
        if self.get_arguments('worker_site'):
            query['worker_sites'] = self.get_arguments('worker_site')
        if self.get_arguments('worker_num'):
            query['worker_num'] = int(self.get_arguments('worker_num')[0])
        if self.get_arguments('workload'):
            query['run_num'] = self.get_arguments('workload')[0]
        if self.get_arguments('bandwidth'):
            query['bandwidth'] = int(self.get_arguments('bandwidth')[0]) * 1000 * 1000
        if self.get_arguments('top'):
            query['limit'] = int(self.get_arguments('top')[0])
        if self.get_arguments('aspect'):
            query['aspect'] = self.get_arguments('aspect')[0]
            
        # create mongo query
        mongo_query = dict(query)
        if 'worker_num' in mongo_query:
            del mongo_query['worker_num']
        if 'worker_sites' in mongo_query:
            del mongo_query['worker_sites']
        if 'limit' in mongo_query:
            del mongo_query['limit']
        if 'aspect' in mongo_query:
            del mongo_query['aspect']
        if 'worker_size' in mongo_query:
            mongo_query['worker_size'] = self._db[DB_NAME]['workflow']['vm_size'].find_one({'name': mongo_query['worker_size']})['value']
        
        # get experiments of interest
        rs = self._db[DB_NAME]['workflow']['experiment'].find(mongo_query, {'_id': 0}).sort('timestamp')
        exp = []
        count = 0
        for r in rs:
            if 'worker_sites' in query:
                sites = [s['site'] for s in r['worker_sites']]
                flag = False
                for s in query['worker_sites']:
                    if s in sites:
                        flag = True
                        break
                if not flag:
                    continue
            if 'worker_num' in query:
                worker_num = sum([int(s['num']) for s in r['worker_sites']])
                if int(query['worker_num']) != worker_num:
                    continue
            if 'limit' in query:
                if count >= int(query['limit']):
                    break
                count += 1
            exp.append(r)
        
        if content_type == 'text/html':
            # renders page
            data = {
                'type': workflow,
                'current_uri': self.request.uri,
                'experiments': exp,
                }
            opts = {
                    'topology': [t for t in self._db[DB_NAME]['workflow']['topology'].find(fields={'_id': 0})],
                    'mode': [m for m in self._db[DB_NAME]['workflow']['mode'].find(fields={'_id': 0})],
                    'sites': [s for s in self._db[DB_NAME]['workflow']['site'].find(fields={'_id': 0})],
                    'worker-size': [w for w in self._db[DB_NAME]['workflow']['vm_size'].find(fields={'_id': 0})],
                }
            self.render('experiments.html', data=data, opts=opts)
        elif content_type == 'application/json':
            # returns data of interest
            if not exp:
                self.set_status(404, 'No data found')
                return
            if 'aspect' not in query:
                self.set_status(400, 'Require specifying aspect')
                return
            else:
                data = self._get_data(query['aspect'], exp)
            if data:
                self.write(data)
            else:
                self.set_status(400, 'No data return')
    
    def _calc_std_dev(self, data):
        '''
        Calculate standard deviation of a list of numbers
        
        :param list data: numbers
        
        '''
        try:
            if len(data) > 1:
                avg = sum(data)/len(data)
                sqr_sum = sum([math.pow(w-avg, 2) for w in data])
                return math.sqrt(sqr_sum/len(data) - 1)
            else:
                return 0
        except ValueError:
            return 0
        
    def _get_data(self, aspect, exp):
        '''
        
        '''
        data = None
        if aspect == 'run':
            runs = [r for r in self._db[DB_NAME]['experiment']['run'].find({'$or': [{'exp_id': e['exp_id']} for e in exp]}, {'_id': 0}).sort('timestamp')]
            data = {
                'label': [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r['timestamp'])) for r in runs],
                'walltime': [int(r['walltime']) for r in runs]    
                } 
            data['std_dev'] = self._calc_std_dev(data['walltime'])
        elif aspect == 'sys_cpu' or aspect == 'sys_mem':
            km = {
                   'max': 'sys_max_cpu_percent' if aspect == 'sys_cpu' else 'sys_max_mem_percent',
                   'min': 'sys_min_cpu_percent' if aspect == 'sys_cpu' else 'sys_min_mem_percent',
                   'avg': 'sys_cpu_percent' if aspect =='sys_cpu' else 'sys_mem_percent',
                   }
            raw = [{'exp_id': s['exp_id'],
                    'max': s[km['max']],
                    'avg': s[km['avg']],
                    'min': s[km['min']],
                    'timestamp': s['timestamp'],
                    'count': s['count']
                    } for s in self._db[DB_NAME]['experiment']['system'].find({'$or': [{'exp_id': e['exp_id']} for e in exp]}, {'_id': 0}).sort('timestamp')]
            res = {}
            for s in raw:
                    if s['exp_id'] not in res:
                        res[s['exp_id']] = {
                                'exp_id': s['exp_id'],
                                'max': s['max'],
                                'min': s['min'],
                                'avg': s['avg'] * s['count'],
                                'count': s['count'],
                                'timestamp': s['timestamp']
                            }
                    else:
                        res[s['exp_id']]['max'] = max(s['max'], res[s['exp_id']]['max'])
                        res[s['exp_id']]['min'] = min(s['min'], res[s['exp_id']]['min'])
                        res[s['exp_id']]['avg'] += s['avg'] * s['count']
                        res[s['exp_id']]['count'] += s['count']
              
            for s in res:
                res[s]['avg'] /= res[s]['count']
                del res[s]['count']
            
            data = {
                'label': [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(res[s]['timestamp'])) for s in res],
                'max': [res[s]['max'] for s in res],
                'min': [res[s]['min'] for s in res],
                'avg': [res[s]['avg'] for s in res],
            }
            
            data['max_std_dev'] = self._calc_std_dev(data['max'])
            data['min_std_dev'] = self._calc_std_dev(data['min'])
            data['avg_std_dev'] = self._calc_std_dev(data['avg'])
        elif aspect == 'sys_read'or aspect == 'sys_write' or aspect == 'sys_send' or aspect == 'sys_recv':
            km = {}
            if aspect == 'sys_read':
                km['val'] = 'sys_read_rate'
            elif aspect == 'sys_write':
                km['val'] = 'sys_write_rate'
            elif aspect == 'sys_send':
                km['val'] = 'sys_send_rate'
            elif aspect == 'sys_recv':
                km['val'] = 'sys_recv_rate'
            raw = [{'exp_id': s['exp_id'],
                    'val': s[km['val']] / 1024 / 1024,
                    'timestamp': s['timestamp'],
                    'count': s['count']
                    } for s in self._db[DB_NAME]['experiment']['system'].find({'$or': [{'exp_id': e['exp_id']} for e in exp]}, {'_id': 0}).sort('timestamp')]
            res = {}
            for s in raw:
                if s['exp_id'] not in res:
                    res[s['exp_id']] = {
                            'max': s['val'],
                            'avg': s['val'],
                            'min': s['val'],
                            'count': s['count'],
                            'timestamp': s['timestamp']
                        }
                else:
                    res[s['exp_id']]['max'] = max(res[s['exp_id']]['max'], s['val'])
                    res[s['exp_id']]['min'] = min(res[s['exp_id']]['min'], s['val'])
                    res[s['exp_id']]['avg'] += s['val']
            for s in res:
                res[s]['avg'] /= res[s]['count']
                del res[s]['count']
                
            data = {
                'label': [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(res[s]['timestamp'])) for s in res],
                'max': [res[s]['max'] for s in res],
                'min': [res[s]['min'] for s in res],
                'avg': [res[s]['avg'] for s in res],
            }
            
            data['max_std_dev'] = self._calc_std_dev(data['max'])
            data['min_std_dev'] = self._calc_std_dev(data['min'])
            data['avg_std_dev'] = self._calc_std_dev(data['avg'])
        return data
        