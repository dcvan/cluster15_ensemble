'''
Created on Feb 10, 2015

@author: dc
'''
import time
import numpy
import pymongo
import matplotlib
import matplotlib.pyplot as plt

db = pymongo.MongoClient()['cluster15']
exp_handle = db['workflow']['experiment']
run_handle = db['experiment']['run']
sys_handle = db['experiment']['system']
job_handle = db['experiment']['job']

vm_sizes = ['Small', 'Medium', 'Large', 'Extra-large']

# matplotlib global settings
matplotlib.rc('font', size=10)
matplotlib.rc('legend', fontsize=10, frameon=False)


def get_experiments(cond, sortby='timestamp'):
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
    elif sortby == 'worker_sites':
        sortby = 'overlap'
        for e in exps:
            e['worker_sites'] = [s['site'] for s in e['worker_sites']]
        caliber = set(exps[0]['worker_sites'])
        print caliber
        for e in exps:
            e['overlap'] = len(set(e['worker_sites'])&caliber)

    exps = [(r[sortby], r['exp_id']) for r in sorted(exps, key=lambda e: e[sortby])]
    cat = {}
    for e in exps:
        if e[0] in cat:
            cat[e[0]].append(e[1])
        else:
            cat[e[0]] = [e[1]]
    return cat 
    
class Analyzer:
    
    def get_analysis(self, cond, sortby, aspect):
        cat = get_experiments(cond, sortby)
        raw = {}
        for g in cat:
            if aspect == 'walltime':
                raw[g] = [r['walltime'] for r in run_handle.find({'exp_id': {'$in': cat[g]}}, {'_id': 0, 'walltime': 1})]
            elif aspect == 'sys_cpu':
                raw[g] = [r['sys_cpu_percent'] for r in sys_handle.find({'exp_id': {'$in': cat[g]}}, {'_id': 0, 'sys_cpu_percent': 1})]
            elif aspect == 'sys_mem':
                raw[g] = [r['sys_mem_percent'] for r in sys_handle.find({'exp_id': {'$in': cat[g]}}, {'_id': 0, 'sys_mem_percent': 1})]
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
        plt.xticks(x, tags, rotation=60 if sortby in ['last_update_time'] else 0, fontsize=8 if sortby in ['last_update_time'] else 10)
        if sortby in ['last_update_time']:
            plt.subplots_adjust(bottom=0.3)
        l1, = plt.plot(x, avg_wt, label='Avg.')
        l2, =  plt.plot(x, max_wt, label='Max.')
        l3, = plt.plot(x, min_wt, label='Min.')
        plt.legend(handles=[l1, l2, l3])
     
        plt.ylim(ymin=0, ymax=plt.ylim()[1] * 1.3)
        
        if sortby in ['master_site', 'worker_sites', 'last_update_time']:
            plt.text(plt.xlim()[1] * 0.02, plt.ylim()[1] * 0.95, 'std. deviation: %.2f' % numpy.std(avg_wt, ddof=1), fontsize=12)        
        
        if sortby == 'worker_size':
            plt.xlabel('Worker size')
        elif sortby == 'bandwidth':
            plt.xlabel('Bandwidth(Mbps)')
        elif sortby == 'num_of_workers':
            plt.xlabel('Number of workers')
        elif sortby == 'workload':
            plt.xlabel('Number of workloads')
            
        if aspect == 'walltime':
            plt.ylabel('Walltime(mins)')  
        elif aspect == 'sys_cpu':
            plt.ylabel('CPU Usage(%)')
        elif aspect == 'sys_mem':
            plt.ylabel('Memory Usage(%)')
            
    def save(self, fname):
        plt.savefig(open('graphs/%s.pdf'%fname, 'wb'), format='pdf')
        plt.clf()

        
if __name__ == '__main__':
    m = Analyzer()
    for asp in ['walltime', 'sys_cpu', 'sys_mem']:
        cond = {
                'type': 'genomic',
                'status': 'finished',
                'workload': 1,
                'deployment': 'standalone'
            }
        m.get_analysis(cond, 'worker_size', asp)
        m.save('%s-genomic-size' % asp)
        
        cond = {
                'type': 'montage',
                'status': 'finished',
                'bandwidth': 100 * 1000 * 1000,
                'num_of_workers': 5,
                'workload': 1,
                'topology': 'intra-rack'
            }
        m.get_analysis(cond, 'worker_size', asp)
        m.save('%s-montage-size' % asp)
        
        cond = {
                'type': 'genomic',
                'status': 'finished',
                'worker_size': 'XOLarge',
                'bandwidth': 100 * 1000 * 1000,
                'num_of_workers': 3,
                'topology': 'intra-rack'
            }
        m.get_analysis(cond, 'workload', asp)
        m.save('%s-genomic-workload' % asp)
        
        cond = {
                'type': 'montage',
                'status': 'finished',
                'worker_size': 'XOLarge',
                'bandwidth': 100 * 1000 * 1000,
                'num_of_workers': 5,
                'topology': 'intra-rack'
            }
        m.get_analysis(cond, 'workload', asp)
        m.save('%s-montage-workload' % asp) 
        
        cond = {
                'type': 'montage',
                'status': 'finished',
                'worker_size': 'XOLarge',
                'num_of_workers': 5,
                'workload': 1,
                'topology': 'intra-rack',
            }
        m.get_analysis(cond, 'bandwidth', asp)
        m.save('%s-montage-bandwidth' % asp)
        
        cond = {
                'type': 'genomic',
                'status': 'finished',
                'worker_size': 'XOLarge',
                'workload': 5,
                'topology': 'intra-rack',
                'master_site': 'sl',
            }
        m.get_analysis(cond, 'num_of_workers', asp)
        m.save('%s-genomic-worker#' % asp)
        
        cond = {
                'type': 'genomic',
                'status': 'finished',
                'workload': 1,
                'worker_size': 'XOLarge',
                'deployment': 'standalone'
        }
        m.get_analysis(cond, 'master_site', asp)
        m.save('%s-genomic-master' % asp)
    
        cond = {
                'type': 'montage',
                'status': 'finished',
                'workload': 1,
                'bandwidth': 100 * 1000 * 1000,
                'num_of_workers': 5,
                'worker_size': 'XOLarge',
                'topology': 'intra-rack'
        }
        m.get_analysis(cond, 'master_site', asp)
        m.save('%s-montage-master' % asp)
            
        cond = {
                'type': 'genomic',
                'status': 'finished',
                'workload': 1,
                'master_site': 'uh',
                'worker_size': 'XOLarge',
                'deployment': 'standalone'
        }
        m.get_analysis(cond, 'last_update_time', asp)
        m.save('%s-genomic-timestamp' % asp)
        
        cond = {
                'type': 'montage',
                'status': 'finished',
                'topology': 'inter-rack',
                'num_of_workers': 4
                }
        m.get_analysis(cond, 'worker_sites', asp)
        m.save('%s-montage-workers' % asp)
    

#     cond = {
#             'type': 'genomic',
#             'status': 'finished',
#             'deployment': 'standalone'
#             }
#     m.get_walltime_by_size(cond)
#     m.save('genomic-size')
