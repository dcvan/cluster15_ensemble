'''
Created on Feb 10, 2015

@author: dc
'''
import time
import numpy
import pymongo
import matplotlib.pyplot as plt

db = pymongo.MongoClient()['cluster15']
exp_handle = db['workflow']['experiment']
run_handle = db['experiment']['run']
sys_handle = db['experiment']['system']
job_handle = db['experiment']['job']

vm_sizes = ['Small', 'Medium', 'Large', 'Extra-large']

class WalltimeAnalyzer:
    
    def get_experiments(self, cond, sortby='timestamp'):
        '''
        
        '''
        exps = [e for e in exp_handle.find(cond, {'_id': 0})]
        if sortby == 'worker_size':
            sortby = 'size'
            for e in exps:
                if e['worker_size'].lower() == 'xosmall':
                    e['size'] = 1
                elif e['worker_size'].lower() == 'xomedium':
                    e['size'] = 2
                elif e['worker_size'].lower() == 'xolarge':
                    e['size'] = 3
                elif e['worker_size'].lower() == 'xoxlarge':
                    e['size'] = 4
        elif sortby == 'last_update_time':
            for e in exps:
                e['last_update_time'] = time.strftime('%m/%d %H:00', time.localtime(e['last_update_time']))
        exps = [(r[sortby], r['exp_id']) for r in sorted(exps, key=lambda e: e[sortby])]
        cat = {}
        for e in exps:
            if e[0] in cat:
                cat[e[0]].append(e[1])
            else:
                cat[e[0]] = [e[1]]
        return cat 
    
    def get_walltime(self, cond, sortby):
        cat = self.get_experiments(cond, sortby)
        raw = {}
        for g in cat:
            raw[g] = [r['walltime'] for r in run_handle.find({'exp_id': {'$in': cat[g]}}, {'_id': 0})]
        tags = raw.keys()
        tags.sort()
        avg_wt = [numpy.average(raw[t]) for t in tags]
        max_wt = [numpy.max(raw[t]) for t in tags]
        min_wt = [numpy.min(raw[t]) for t in tags]
        if sortby == 'worker_size':
            tags = [vm_sizes[i - 1] for i in tags]
        elif sortby == 'bandwidth':
            tags = [i / (1000 * 1000) for i in tags]
        elif sortby == 'master_site':
            tags = [i.upper() for i in tags]
        x = [i for i in range(0, len(tags))]
        plt.xticks(x, tags, rotation=60if sortby in ['last_update_time'] else 'horizontal')
        if sortby in ['last_update_time']:
            plt.subplots_adjust(bottom=0.3)
        l1, = plt.plot(x, avg_wt, label='Avg.')
#         if sortby in ['master_site', 'last_update_time']:
#             plt.legend(handles=[l1])
#         else:
        l2, =  plt.plot(x, max_wt, label='Max.')
        l3, = plt.plot(x, min_wt, label='Min.')
        plt.legend(handles=[l1, l2, l3])

        plt.ylim(ymin=0)
        if sortby in ['master_site', 'last_update_time', 'workload']:
            plt.ylim(ymax=plt.ylim()[1] + 100)
        
        if sortby == 'worker_size':
            plt.xlabel('Worker size')
        elif sortby == 'bandwidth':
            plt.xlabel('Bandwidth(Mbps)')
        elif sortby == 'num_of_workers':
            plt.xlabel('Number of workers')
        elif sortby == 'workload':
            plt.xlabel('Number of workloads')
        plt.ylabel('Walltime(mins)')        
    
    def save(self, fname):
        plt.savefig(open('graphs/wt-%s.pdf'%fname, 'wb'), format='pdf')
        plt.clf()
        
        
if __name__ == '__main__':
    m = WalltimeAnalyzer()
    cond = {
            'type': 'montage',
            'status': 'finished',
            'bandwidth': 100 * 1000 * 1000,
            'num_of_workers': 5,
            'workload': 1,
            'topology': 'intra-rack'
        }
    m.get_walltime(cond, 'worker_size')
    m.save('montage-size')
    
    cond = {
            'type': 'genomic',
            'status': 'finished',
            'worker_size': 'XOLarge',
            'bandwidth': 100 * 1000 * 1000,
            'num_of_workers': 3,
            'topology': 'intra-rack'
        }
    m.get_walltime(cond, 'workload')
    m.save('genomic-workload')
    
    cond = {
            'type': 'montage',
            'status': 'finished',
            'worker_size': 'XOLarge',
            'num_of_workers': 5,
            'workload': 1,
            'topology': 'intra-rack'
        }
    m.get_walltime(cond, 'bandwidth')
    m.save('montage-bandwidth')
    
    cond = {
            'type': 'genomic',
            'status': 'finished',
            'worker_size': 'XOLarge',
            'workload': 5,
            'topology': 'intra-rack',
            'master_site': 'sl',
        }
    m.get_walltime(cond, 'num_of_workers')
    m.save('genomic-worker#')
    
    cond = {
            'type': 'genomic',
            'status': 'finished',
            'workload': 1,
            'worker_size': 'XOLarge',
            'deployment': 'standalone'
    }
    m.get_walltime(cond, 'master_site')
    m.save('genomic-master')

    cond = {
            'type': 'montage',
            'status': 'finished',
            'workload': 1,
            'bandwidth': 100 * 1000 * 1000,
            'num_of_workers': 5,
            'worker_size': 'XOLarge',
            'topology': 'intra-rack'
    }
    m.get_walltime(cond, 'master_site')
    m.save('montage-master')
        
    cond = {
            'type': 'genomic',
            'status': 'finished',
            'workload': 1,
            'master_site': 'uh',
            'worker_size': 'XOLarge',
            'deployment': 'standalone'
    }
    m.get_walltime(cond, 'last_update_time')
    m.save('genomic-timestamp')
    
#     cond = {
#             'type': 'genomic',
#             'status': 'finished',
#             'deployment': 'standalone'
#             }
#     m.get_walltime_by_size(cond)
#     m.save('genomic-size')
