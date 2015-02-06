'''
Created on Jan 13, 2015

@author: dc
'''
import os
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
        content_type = check_content_type(self)
        if not content_type:
            return
        if content_type == 'text/html':
            data = {
                    'topology': ['intra-rack', 'inter-rack'],
                    'deployment': ['standalone', 'multinode'],
                    'site': [s for s in self._db[DB_NAME]['workflow']['site'].find(fields={'_id': 0})],
                    'worker_size': [w for w in self._db[DB_NAME]['workflow']['vm_size'].find(fields={'_id': 0})],
                    'storage_type': ['native', 'ISCSI'],
                }
            self.render('workflows.html', workflows=[w for w in self._db[DB_NAME]['workflow']['type'].find({}, {'_id': 0}).sort('name')], data=data)
        elif content_type == 'application/json':
            self.write({'workflows': [w for w in self._db[DB_NAME]['workflow']['type']]})
            self.finish()
    
    def post(self):
        '''
        POST method: create new experiment
        
        '''
        content_type = check_content_type(self)
        if not content_type:
            return
        if content_type == 'application/json':
            try:
                data = json.loads(self.request.body)
                if set(data.keys()) == set(['type', 'topology', 'deployment', 
                                           'master_site', 'worker_sites', 'worker_size', 'storage_type',
                                           'filesystem', 'workload', 'reservation', 'num_of_workers']):
                    # TO-DO: data validation
                    data['exp_id'] = str(uuid.uuid4())
                    data['status'] = 'submitted'
                    data['create_time'] = int(time.time())
                    data['last_update_time'] = int(time.time())
                    for w in data['worker_sites']:
                        w['num'] = int(w['num'])
                    data['num_of_workers'] = int(data['num_of_workers'])
                    data['workload'] = int(data['workload'])
                    data['reservation'] = int(data['reservation'])
                    if 'storage_size' in data:
                        data['storage_size'] = int(data['storage_size'])
                    if 'bandwidth' in data:
                        data['bandwidth'] = int(data['bandwidth'])
                    self._db[DB_NAME]['workflow']['experiment'].insert(data)
                    self.write({
                                'exp_id': data['exp_id'],
                                'type': data['type'],
                                'create_time': int(time.time())
                            })
                else:
                    self.set_status(400, 'Missing required field(s)')
            except ValueError:
                self.set_status(400, 'Invalid user data');
        else:
            self.set_status(501, 'Not implemented yet')
            
class DeploymentRender(tornado.web.RequestHandler):
    '''
    Renders deployment info
     
    '''
    def initialize(self, db):
        '''
        Init
        
        '''
        self._db = db
        
    def get(self, deployment):
        '''
        GET method: get file system info
        
        '''
        content_type = check_content_type(self)
        if not content_type: return
        if content_type == 'application/json':
            fs = self._db[DB_NAME]['workflow']['fs'].find_one({'deployment': deployment})
            if fs:
                self.write({'fs': fs['types']})
            else:
                self.set_status(204, "No content found")
                return
            
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
        if not content_type: return
        if content_type == 'text/html':
            exp['worker_size'] = self._db[DB_NAME]['workflow']['vm_size'].find_one({'value': exp['worker_size']}, {'_id': 0})['name']
            exp['create_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp['create_time']))
            exp['workers'] = [w for w in self._db[DB_NAME]['experiment']['worker'].find({'exp_id': exp_id}, {'_id': 0}).sort('host')]
            exp['runs'] = [r for r in self._db[DB_NAME]['experiment']['run'].find({'exp_id': exp_id}, {'_id': 0}).sort('run_id')]
            if 'bandwidth' in exp and exp['bandwidth']: exp['bandwidth'] /= (1000 * 1000)
            self.render('experiment.html', data=exp)
        elif content_type == 'application/json':
            del exp['create_time']
            del exp['exp_id']
            del exp['status']
            self.write(exp)
            
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
        else:
            self._db[DB_NAME]['workflow']['experiment'].update({'exp_id': exp_id}, {'$set': {'status': 'redo'}})
        self._db[DB_NAME]['experiment']['worker'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['job'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['system'].remove({'exp_id': exp_id})
        self._db[DB_NAME]['experiment']['run'].remove({'exp_id': exp_id})
        
class ManifestRenderer(tornado.web.RequestHandler):
    '''
    Renders manifest info
    
    '''
    def initialize(self, db):
        '''
        Init 
        
        '''
        self._db = db
        
    def get(self, workflow, exp_id):
        '''
        GET method: renders manifest info
        
        '''
        content_type = check_content_type(self)
        if not content_type: return
        if content_type == 'application/json':
            exp = self._db[DB_NAME]['workflow']['experiment'].find_one({'exp_id': exp_id}, {'_id': 0})
            if exp and exp['type'] == workflow:
                self.write({'manifest': os.linesep.join([l for l in self._get_manifest(exp).splitlines() if l])})
            else:
                self.set_status(404, 'Experiment not found')
        else:
            self.set_status(501, 'Not implemented yet')
            
    def post(self, workflow, exp_id):
        '''
        POST method: download the manifest
        
        '''
        content_type = check_content_type(self)
        if not content_type: return
        if content_type == 'application/x-www-form-urlencoded':
            exp = self._db[DB_NAME]['workflow']['experiment'].find_one({'exp_id': exp_id}, {'_id': 0})
            if exp and exp['type'] == workflow:
                self.set_header('Content-Type', 'application/rdf+xml')
                self.set_header('Content-Disposition', 'attachment;filename=%s' % '-'.join([exp['master_site'], exp['exp_id']]))
                self.write(os.linesep.join([l for l in self._get_manifest(exp).splitlines() if l]))
            else:
                self.set_status(404, 'Experiment not found')
        else:
            self.set_status(501, 'Not implemented yet')
            
    def _get_manifest(self, exp):
        '''
        Generate manifest
        
        :param dict exp: experiment parameters
        :rtype str
        :raise KeyEror
        
        '''
        exp['image'] = self._db[DB_NAME]['workflow']['type'].find_one({'name': exp['type']}, {'_id':0, 'image': 1})['image']
        t = self._db[DB_NAME]['workflow']['type'].find_one({'name': exp['type']}, {'_id': 0, 'postscript': 1})
        if 'bandwidth' in exp and exp['deployment'] == 'multinode' and not exp['bandwidth']:
            exp['bandwidth'] = 500000000
        if 'storage_size' in exp and exp['storage_type'].lower() == 'iscsi' and not exp['storage_size']:
            exp['storage_size'] = 50
        exp['resource_type'] = 'BareMetalCE' if exp['worker_size'] == 'ExoGENI-M4' else 'VM'
        exp['executables'] = self._db[DB_NAME]['workflow']['type'].find_one({'name': exp['type']}, {'_id': 0})['executables']
        exp['master_postscript'] = jinja2.Template(t['postscript']['master']).render(param={
                                                                                        'exp_id': exp['exp_id'],
                                                                                        'deployment': exp['deployment'],
                                                                                        'filesystem': exp['filesystem'],
                                                                                        'site': exp['master_site'],
                                                                                        'executables': exp['executables'],
                                                                                        'num_of_workers': exp['num_of_workers'],
                                                                                        'workload': exp['workload']
                                                                                            })
        if 'worker' in t['postscript']:
            for w in exp['worker_sites']:
                w['worker_postscript'] = jinja2.Template(t['postscript']['worker']).render(param={
                                                                                            'exp_id': exp['exp_id'],
                                                                                            'filesystem': exp['filesystem'],
                                                                                            'site': w['site'],
                                                                                            'executables': exp['executables']   
                                                                                            })
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
            return
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
            res['label'] = [s['timestamp'] for s in stat ]
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
        content_type = check_content_type(self)
        if not content_type: return
        if not self._db[DB_NAME]['workflow']['type'].find_one({'name': workflow}):
            self.set_status(404, 'Workflow not available')
            return
        if content_type == 'text/html':
            data = {
                'type': workflow,
                'topology': ['intra-rack', 'inter-rack'],
                'deployment': ['standalone', 'multinode'],
                'sites': [s for s in self._db[DB_NAME]['workflow']['site'].find(fields={'_id': 0})],
                'worker-size': [w for w in self._db[DB_NAME]['workflow']['vm_size'].find(fields={'_id': 0})],
                }
            self.render('experiments.html', data=data)
        elif content_type == 'application/json':
            try:
                query = {'$and': [{'type': workflow, 'status': self.get_argument('status')}]} 
                args = [ 'deployment', 'topology', 'master_site', 'worker_site', 'num_of_workers', 'workload', 'bandwidth', 'start_time', 'end_time']
                for i in args:
                    if self.get_arguments(i):
                        if i == 'worker_site':
                            query['$and'].append({'worker_sites': {'$elemMatch': {'site': {'$in': self.get_arguments(i)}}}})
                        elif i == 'bandwidth':
                            query['$and'].append({i: int(self.get_arguments(i)[0]) * 1000 * 1000})
                        elif i == 'start_time':
                            query['$and'].append({'create_time': {'$gt': int(self.get_arguments(i)[0])}})
                        elif i == 'end_time':
                            query['$and'].append({'create_time': {'$lt': int(self.get_arguments(i)[0])}})
                        elif i in ['num_of_workers', 'workload']:
                            query['$and'].append({i: int(self.get_arguments(i)[0])})
                        else:
                            query['$and'].append({i: {'$in': self.get_arguments(i)}})
                
                sort_by = self.get_arguments('sort')[0] if self.get_arguments('sort') else 'last_update_time'
                top = int(self.get_arguments('top'))[0] if self.get_arguments('top') else None
            
                res = self._db[DB_NAME]['workflow']['experiment'].find(query, {'_id': 0}).sort(sort_by)
                if res.count() > 0:
                    if top: res = res.limit(top)
                    exp = [e for e in res if e]
                    for e in exp: self._update_status(e)
                    self.write({'result': exp})
                else:
                    self.set_status(204, 'No data found')
            except ValueError as ve:
                self.set_status(400, 'Invalid user data: %s' % str(ve))
            except tornado.web.MissingArgumentError:
                self.set_status(400, 'Argument "status" is required')
                
    def _update_status(self, exp):
        '''
        Update the status of the experiment
        
        :param dict exp: an experiment instance
        
        '''
        if exp['status'] == 'submitted' or exp['status'] == 'redo' or exp['status'] == 'setup':
            finished = self._db[DB_NAME]['experiment']['run'].find({'exp_id': exp['exp_id']}, {'_id': 0}).count()
            expected = self._db[DB_NAME]['workflow']['experiment'].find_one({'exp_id': exp['exp_id']}, {'_id': 0, 'workload': 1})['workload']
            if finished == expected:
                self._db[DB_NAME]['workflow']['experiment'].update({'exp_id': exp['exp_id']}, {'$set': {'status': 'finished'}})
                exp['status'] = 'finished'
            else:
                discovered = self._db[DB_NAME]['experiment']['worker'].find({'exp_id': exp['exp_id']}, {'_id': 0}).count()
                expected = self._db[DB_NAME]['workflow']['experiment'].find_one({'exp_id': exp['exp_id']}, {'_id': 0, 'num_of_workers': 1})['num_of_workers']
                if discovered == expected:
                    self._db[DB_NAME]['workflow']['experiment'].update({'exp_id': exp['exp_id']}, {'$set': {'status': 'running'}})
                    exp['status'] = 'running'
        elif exp['status'] == 'running':
            finished = self._db[DB_NAME]['experiment']['run'].find({'exp_id': exp['exp_id']}, {'_id': 0}).count()
            expected = self._db[DB_NAME]['workflow']['experiment'].find_one({'exp_id': exp['exp_id']}, {'_id': 0, 'workload': 1})['workload']
            if finished == expected:
                self._db[DB_NAME]['workflow']['experiment'].update({'exp_id': exp['exp_id']}, {'$set': {'status': 'finished'}})
                exp['status'] = 'finished'

class AnalysisRenderer(tornado.web.RequestHandler):
    '''
    Renders analysis data
    
    '''
    def initialize(self, db):
        '''
        Init
        
        :param pymongo.MongoClient db: the MongoDB connection
         
        '''
        self._db = db
        
        
    def post(self, workflow):
        '''
        POST method
        
        :param str workflow: the workflow type
        
        '''
        content_type = check_content_type(self)
        if not content_type: return
        if not self._db[DB_NAME]['workflow']['type'].find_one({'name': workflow}):
            self.set_status(404, 'Workflow not found')
            return
        if content_type == 'application/json':
            try:
                query = json.loads(self.request.body)
                if 'aspect' not in query:
                    self.set_status(400, '"aspect" field is required')
                    return
                if query['aspect'] not in ['walltime', 'sys_cpu', 'sys_mem', 'sys_read', 'sys_write', 'sys_send', 'sys_recv']: 
                    self.set_status(400, 'Invalid aspect: %s' % query['aspect'])
                    return
                query['use'] = 'regular' if 'use' not in query or query['use'] not in ['regular', 'chart'] else query['use']
                query['exp_ids'] = query['exp_ids'] if 'exp_ids' in query and query['exp_ids'] else [e['exp_id'] for e in 
                                            self._db[DB_NAME]['workflow']['experiment'].find({'type': workflow}, {'_id': 0, 'exp_id': 1}).sort('timestamp')]
                data = self._get_data(query)
                if data:
                    self.write(data)
                else:
                    self.set_status(204, 'No data found')
            except ValueError as ve:
                self.set_status(400, 'Invalid user data: %s' % str(ve))
        else:
            self.set_status(501, 'Not implemented yet')

    def _get_data(self, query):
        '''
        Get data from DB
        
        :param dict query: parameters
        :rtype dict
        
        '''
        raw = None
        if len(query['aspect']) >= 3 and query['aspect'][0:3] == 'sys':
            exp = [e for e in self._db[DB_NAME]['experiment']['system'].find({'$or': [{'exp_id': i } for i in query['exp_ids']]}, {'_id': 0})]
            if not exp: return exp
            kw = {}
            if query['aspect'] in ['sys_cpu', 'sys_mem']:
                kw['max'] = 'sys_max_%s_percent' % query['aspect'].split('_')[1]
                kw['min'] = 'sys_min_%s_percent' % query['aspect'].split('_')[1]
                kw['avg'] = '%s_percent' % query['aspect']
                raw = [{'exp_id': e['exp_id'],
                     'max': int(e[kw['max']]),
                     'min': int(e[kw['min']]),
                     'avg': int(e[kw['avg']]),
                     'timestamp': int(e['timestamp']),
                     'count': int(e['count'])
                     } for e in exp]
            else:
                kw['value'] = '%s_rate' % query['aspect']
                raw = [{'exp_id': e['exp_id'],
                     'value': int(e[kw['value']]) / (1024 * 1024),
                     'timestamp': int(e['timestamp']),
                     } for e in exp]
        elif query['aspect'] == 'walltime':
            exp = [e for e in self._db[DB_NAME]['experiment']['run'].find({'$or': [{'exp_id': i } for i in query['exp_ids']]}, {'_id': 0})]
            if not exp: return exp
            raw =  [{'exp_id': e['exp_id'],
                     'value': int(e['walltime']) if e['walltime'] else 0,
                     'timestamp': int(e['timestamp']),
                     } for e in exp]
        
        if not raw: # unlikely
            return raw
        elif query['use'] == 'regular':
            return {'result': raw}
        elif query['use'] == 'chart':
            return self._convert_to_chart_data(raw, query['aspect'], query['exp_ids'])

    def _convert_to_chart_data(self, data, aspect, order):
        '''
        Convert raw data to usable data for Chart.js
        
        :param list data: data
        :param str aspect: aspect the data is related on
        :param list order: the initial order of exp_ids
        :param dict
        
        '''
        res, raw = {}, {}
        if len(aspect) > 3 and aspect[:3] == 'sys':
            for k in data:
                exp_id = k['exp_id']
                if exp_id not in raw:
                    raw[exp_id] = {
                            'exp_id': exp_id,
                            'max': k['max' if aspect in ['sys_cpu', 'sys_mem'] else 'value'],
                            'min': k['min' if aspect in ['sys_cpu', 'sys_mem'] else 'value'],
                            'avg': (k['avg'] * k['count']) if aspect in ['sys_cpu', 'sys_mem'] else k['value'],
                            'timestamp': k['timestamp'],
                            'count': k['count'] if aspect in ['sys_cpu', 'sys_mem'] else 1
                        }
                else:
                    raw[exp_id]['max'] = max(raw[exp_id]['max'], k['max' if aspect in ['sys_cpu', 'sys_mem'] else 'value'])
                    raw[exp_id]['min'] = min(raw[exp_id]['min'], k['min' if aspect in ['sys_cpu', 'sys_mem'] else 'value'])
                    raw[exp_id]['avg'] += (k['avg'] * k['count']) if aspect in ['sys_cpu', 'sys_mem'] else k['value']
                    raw[exp_id]['count'] += k['count'] if aspect in ['sys_cpu', 'sys_mem'] else 1
            res['timestamp'], res['exp_id'], res['max'], res['min'], res['avg'] = [], [], [], [], []
            for k in order:
                if k not in raw: continue
                res['exp_id'].append(k)
                res['timestamp'].append(raw[k]['timestamp'])
                res['max'].append(raw[k]['max'])
                res['min'].append(raw[k]['min'])
                res['avg'].append(raw[k]['avg']/raw[k]['count'])
            res['overall_max'] = max(res['max'])
            res['overall_min'] = min(res['min'])
            res['overall_avg'] = sum(res['avg'])/len(res['avg']) if len(res['avg']) else 0
            res['max_std_dev'] = self._calc_std_dev(res['max'])
            res['min_std_dev'] = self._calc_std_dev(res['min'])
            res['avg_std_dev'] = self._calc_std_dev(res['avg'])
        elif aspect == 'walltime':
            for k in data:
                exp_id = k['exp_id']
                if exp_id not in res:
                    raw[exp_id] = {
                            'exp_id': exp_id,
                            'timestamp': k['timestamp'],
                            'count': 1,
                            'avg': k['value']
                        }
                else:
                    raw[exp_id]['avg'] += k['value']
                    raw[exp_id]['count'] += 1
            res['exp_id'], res['timestamp'], res['values']= [], [], []
            for k in order:
                if k not in raw: continue
                res['exp_id'].append(k)
                res['timestamp'].append(raw[k]['timestamp'])
                res['values'].append(raw[k]['avg']/raw[k]['count'])
            res['overall_max'] = max(res['values'])
            res['overall_min'] = min(res['values'])
            res['overall_avg'] = sum(res['values'])/len(res['values']) if len(res['values']) else 0
            res['avg_std_dev'] = self._calc_std_dev(res['values'])
        return res
    
    def _calc_std_dev(self, data):
        '''
        Calculate standard deviation
        
        :param list data: a list of numbers
        :rtype float
        
        '''
        try:
            if len(data) <= 1:
                return 0.0
            avg = sum(data)/len(data)
            sqr_sum = sum([math.pow(int(e) - avg, 2) for e in data])
            return float('%.3f'%math.sqrt(sqr_sum/len(data) - 1))
        except ValueError:
            return 0.0
        