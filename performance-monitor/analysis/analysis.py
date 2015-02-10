'''
Created on Feb 10, 2015

@author: dc
'''
import numpy
import pymongo
import matplotlib.pyplot as plt

from matplotlib.patches import Polygon



def plot_walltime(condition, name):
    exps = db['experiment']['run'].find(condition, {'_id': 0})
    plt.plot([e['walltime'] for e in exps])
    plt.ylabel('Walltime(mins)')
    plt.savefig(open('graphs/%s.pdf'%(name), 'wb'), format='pdf')

db = pymongo.MongoClient()['cluster15']
exp_handle = db['workflow']['experiment']
run_handle = db['experiment']['run']
sys_handle = db['experiment']['system']
job_handle = db['experiment']['job']

class Analyzer:
    
    def get_experiments(self, cond, sortby='timestamp'):
        '''
        
        '''
        exps = [e for e in exp_handle.find(cond, {'_id': 0})]
        if sortby == 'worker_size':
            for e in exps:
                if e['worker_size'].lower() == 'xosmall':
                    e['size'] = 1
                elif e['worker_size'].lower() == 'xomedium':
                    e['size'] = 2
                elif e['worker_size'].lower() == 'xolarge':
                    e['size'] = 3
                elif e['worker_size'].lower() == 'xoxlarge':
                    e['size'] = 4
            return [r for r in sorted(exps, key=lambda e: e['size'])]
        else:
            return [r for r in sorted(exps, key=lambda e: e[sortby])]
        
    def get_walltime_by_size(self, cond):
        exps = self.get_experiments(cond, 'worker_size')
        groups = {}
        for e in exps:
            if e['worker_size'] in groups:
                groups[e['worker_size']].append(e['exp_id'])
            else:
                groups[e['worker_size']] = [e['exp_id']]
        raw = {}
        for g in groups:
            for r in run_handle.find({'exp_id': {'$in': groups[g]}}):
                if g in raw:
                    raw[g].append(r['walltime'])
                else:
                    raw[g] = [r['walltime']]
        tags = set([(e['worker_size'], e['size']) for e in exps])
        sorted_tags = sorted(tags, key=lambda t: t[1])
        tags = [t[0] for t in sorted_tags]
        data = [numpy.average(raw[t]) for t in tags]
        tags = ['%s(%d)'%(t, len(raw[t])) for t in tags]
        x = [i for i in range(0, len(data))]
        plt.xticks(x, tags)
        l, = plt.plot(x, data, label='Average')
        plt.legend(handles=[l])
        plt.xlabel('Worker Size')
        plt.ylabel('Walltime(mins)')
        
    def get_walltime_by_workload(self, cond):
        exps = self.get_experiments(cond, 'workload')
        groups = {}
        for e in exps:
            if e['workload'] in groups:
                groups[e['workload']].append(e['exp_id'])
            else:
                groups[e['workload']] = [e['exp_id']]
        raw = {}
        for g in groups:
            for r in run_handle.find({'exp_id': {'$in': groups[g]}}):
                if g in raw:
                    raw[g].append(r['walltime'])
                else:
                    raw[g] = [r['walltime']]
        tags = raw.keys()
        tags.sort()
        data = [numpy.average(raw[t]) for t in tags]
        tags = ['%d(%d)' % (t, len(raw[t])/t) for t in tags]
        x = [i for i in range(0, len(data))]
        plt.xticks(x, tags)
        l, = plt.plot(x, data, label='Average')
        plt.legend(handles=[l])
        plt.xlabel('Number of Workloads')
        plt.ylabel('Walltime(mins)')    
        
    def get_walltime_by_bandwidth(self, cond):
        exps = self.get_experiments(cond, 'bandwidth')
        groups = {}
        for e in exps:
            e['bandwidth'] /= (1000 * 1000)
            if e['bandwidth'] in groups:
                groups[e['bandwidth']].append(e['exp_id'])
            else:
                groups[e['bandwidth']] = [e['exp_id']]
        raw = {}
        for g in groups:
            for r in run_handle.find({'exp_id': {'$in': groups[g]}}):
                if g in raw:
                    raw[g].append(r['walltime'])
                else:
                    raw[g] = [r['walltime']]
        tags = raw.keys()
        tags.sort()
        data = [numpy.average(raw[t]) for t in tags]
        tags = ['%d(%d)' % (t, len(raw[t])) for t in tags]
        x = [i for i in range(0, len(data))]
        plt.xticks(x, tags)
        l, = plt.plot(x, data, label='Average')
        plt.legend(handles=[l])
        plt.xlabel('Bandwidth(Mbps)')
        plt.ylabel('Walltime(mins)')  
        
    def get_walltime_by_worker_num(self, cond):
        exps = self.get_experiments(cond, 'num_of_workers')
        groups = {}
        for e in exps:
            if e['num_of_workers'] in groups:
                groups[e['num_of_workers']].append(e['exp_id'])
            else:
                groups[e['num_of_workers']] = [e['exp_id']]
        raw = {}
        for g in groups:
            for r in run_handle.find({'exp_id': {'$in': groups[g]}}):
                if g in raw:
                    raw[g].append(r['walltime'])
                else:
                    raw[g] = [r['walltime']]
        tags = raw.keys()
        tags.sort()
        data = [numpy.average(raw[t]) for t in tags]
        tags = ['%d(%d)' % (t, len(raw[t])) for t in tags]
        x = [i for i in range(0, len(data))]
        plt.xticks(x, tags)
        l, = plt.plot(x, data, label='Average')
        plt.legend(handles=[l])
        plt.xlabel('Number of workers')
        plt.ylabel('Walltime(mins)')  
    
    def save(self, fname):
        plt.savefig(open('graphs/%s.pdf'%fname, 'wb'), format='pdf')
        plt.clf()
        
        
if __name__ == '__main__':
    m = Analyzer()
    cond = {
            'type': 'montage',
            'status': 'finished',
            'bandwidth': 100 * 1000 * 1000,
            'num_of_workers': 5,
            'workload': 1,
            'topology': 'intra-rack'
        }
    m.get_walltime_by_size(cond)
    m.save('wt-montage-size')
    
    cond = {
            'type': 'genomic',
            'status': 'finished',
            'worker_size': 'XOLarge',
            'bandwidth': 100 * 1000 * 1000,
            'num_of_workers': 3,
            'topology': 'intra-rack'
        }
    m.get_walltime_by_workload(cond)
    m.save('wt-genomic-workload')
    
    cond = {
            'type': 'montage',
            'status': 'finished',
            'worker_size': 'XOLarge',
            'num_of_workers': 5,
            'workload': 1,
            'topology': 'intra-rack'
        }
    m.get_walltime_by_bandwidth(cond)
    m.save('wt-montage-bandwidth')
    
    cond = {
            'type': 'genomic',
            'status': 'finished',
            'worker_size': 'XOLarge',
            'workload': 5,
            'topology': 'intra-rack',
            'master_site': 'sl',
        }
    m.get_walltime_by_worker_num(cond)
    m.save('wt-genomic-worker#')
    
#     cond = {
#             'type': 'genomic',
#             'status': 'finished',
#             'deployment': 'standalone'
#             }
#     m.get_walltime_by_size(cond)
#     m.save('genomic-size')
