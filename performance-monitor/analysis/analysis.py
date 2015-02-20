'''
Created on Feb 10, 2015

@author: dc
'''
import time
import numpy
import pymongo
import matplotlib
import matplotlib.pyplot as plt

from matplotlib.pyplot import legend

db = pymongo.MongoClient()['cluster15']
exp_handle = db['workflow']['experiment']
run_handle = db['experiment']['run']
sys_handle = db['experiment']['system']
job_handle = db['experiment']['job']

vm_sizes = ['Small', 'Medium', 'Large', 'XLarge']
weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
styles = ['rD-', 'bH:', 'g.-.']
labels = ['Exomic', 'Montage']
# matplotlib global settings
matplotlib.rc('font', size=8)
matplotlib.rc('legend', fontsize=12)

def get_experiments(cond, sortby='timestamp'):
    '''
    
    '''
    exps = [e for e in exp_handle.find(cond, {'_id': 0})]
    if sortby == 'worker_size':
        for e in exps:
            if e['worker_size'].lower() == 'xosmall':
                e['worker_size'] = 'Small'
            elif e['worker_size'].lower() == 'xomedium':
                e['worker_size'] = 'Medium'
            elif e['worker_size'].lower() == 'xolarge':
                e['worker_size'] = 'Large'
            elif e['worker_size'].lower() == 'xoxlarge':
                e['worker_size'] = 'XLarge'
    elif sortby == 'daytime' or sortby == 'weekday':
        for e in exps:
            e[sortby] = time.strftime('%H:00' if sortby == 'daytime' else '%A', time.localtime(e['last_update_time']))
    elif sortby == 'worker_sites':
        sortby = 'overlap'
        for e in exps:
            e['worker_sites'] = [s['site'] for s in e['worker_sites']]
        caliber = set(exps[0]['worker_sites'])
        for e in exps:
            e['overlap'] = len(caliber) - len(set(e['worker_sites'])&caliber)
    sites = {}
    for e in exps:
        if e['master_site'] in sites:
            sites[e['master_site']] += 1
        else:
            sites[e['master_site']] = 1
    print sites
    exps = [(r[sortby], r['exp_id']) for r in sorted(exps, key=lambda e: e[sortby])]
    cat = {}
    if sortby == 'worker_size':
        for s in vm_sizes:
            cat[s] = []
    elif sortby == 'workload':
        for w in range(1, 9):
            cat[w] = []
    elif sortby == 'bandwidth':
        for w in range(100, 600, 100):
            cat[w] = []
    elif sortby == 'num_of_workers':
        for w in range(1, 6):
            cat[w] = []
    for e in exps:
        if sortby == 'bandwidth':
            cat[e[0] / (1000 * 1000)].append(e[1])
        else:
            cat[e[0]].append(e[1])
    return cat 
    
class Analyzer:

    def analyze(self, conds, sortby):
        cat = [get_experiments(c, sortby) for c in conds]
        if sortby in ['worker_size']:
            tags = sorted(cat[0].keys(), key=vm_sizes.index)
        else:
            tags = cat[0].keys()
            tags.sort()
        g_wt_raw, g_sys_raw, m_wt_raw, m_sys_raw = {}, {}, {}, {}
        for group in tags:
                g_wt_raw[group] = [d['walltime'] for d in run_handle.find({'exp_id': {'$in': cat[0][group]}}, {'_id': 0, 'walltime': 1})]
                g_sys_raw[group] = [d for d in sys_handle.find({'exp_id': {'$in': cat[0][group]}}, {'_id': 0})]
                m_wt_raw[group] = [d['walltime'] for d in run_handle.find({'exp_id': {'$in': cat[1][group]}}, {'_id': 0, 'walltime': 1})]
                m_sys_raw[group] = [d  for d in sys_handle.find({'exp_id': {'$in': cat[1][group]}}, {'_id': 0})]
        x = range(0, len(tags))
        #walltime
        plt.figure(1)
        ax0 = plt.subplot(321)
        ax0.plot(x, [numpy.average(g_wt_raw[k]) if g_wt_raw[k] else None for k in tags], styles[0], markersize=5, label=labels[0])
        ax0.plot(x, [numpy.average(m_wt_raw[k]) if m_wt_raw[k] else None for k in tags], styles[1], markersize=5, label=labels[1])
        ax0.set_xticks(x)
        ax0.set_xticklabels(tags)
        ax0.set_ylabel('Walltime(mins)')
        
        #cpu 
        ax1 = plt.subplot(322)
        ax1.plot(x, [numpy.average([d['sys_cpu_percent'] for d in g_sys_raw[k]]) if g_sys_raw[k] else None for k in tags], styles[0], markersize=5, label=labels[0])
        ax1.plot(x, [numpy.average([d['sys_cpu_percent'] for d in m_sys_raw[k]]) if m_sys_raw[k] else None for k in tags], styles[1], markersize=5, label=labels[1])
        ax1.set_xticks(x)
        ax1.set_xticklabels(tags)
        if sortby == 'worker_size':
            ax1.set_ylim(ymax=105)
        elif sortby == 'workload':
            ax1.set_ylim(94, 100)
        ax1.set_ylabel('CPU util.(%)')

        #mem
        ax2 = plt.subplot(323)
        ax2.plot(x, [numpy.average([d['sys_mem_percent'] for d in g_sys_raw[k]]) if g_sys_raw[k] else None for k in tags], styles[0], markersize=5, label=labels[0])
        ax2.plot(x, [numpy.average([d['sys_mem_percent'] for d in m_sys_raw[k]]) if m_sys_raw[k] else None for k in tags], styles[1], markersize=5, label=labels[1])
        ax2.set_xticks(x)
        ax2.set_xticklabels(tags)
        ax2.set_ylabel('Memory util.(%)')
        
        #read rate
        ax3 = plt.subplot(324)
        ax3.plot(x, [numpy.average([d['sys_read_rate'] / (1024 * 1024) for d in g_sys_raw[k]]) if g_sys_raw[k] else None for k in tags], styles[0], markersize=5, label=labels[0])
        ax3.plot(x, [numpy.average([d['sys_read_rate'] / (1024 * 1024) for d in m_sys_raw[k]]) if m_sys_raw[k] else None for k in tags], styles[1], markersize=5, label=labels[1])
        ax3.set_xticks(x)
        ax3.set_xticklabels(tags)
        ax3.set_ylabel('Read rate(MB/s)')
        
        #write rate
        ax4 = plt.subplot(325)
        l1, = ax4.plot(x, [numpy.average([d['sys_write_rate'] / (1024 * 1024) for d in g_sys_raw[k]]) if g_sys_raw[k] else None for k in tags], styles[0], markersize=5, label=labels[0])
        l2, = ax4.plot(x, [numpy.average([d['sys_write_rate'] / (1024 * 1024) for d in m_sys_raw[k]]) if m_sys_raw[k] else None for k in tags], styles[1], markersize=5, label=labels[1])
        ax4.set_xticks(x)
        ax4.set_xticklabels(tags)
        ax4.set_ylabel('Write rate(MB/s)')

        legend(bbox_to_anchor=(1.45, 0.4), loc=2, ncol=1, borderaxespad=0, borderpad=0.7, labelspacing=1, handlelength=3, handles=[l1, l2])
        plt.tight_layout()
         
    def save(self, fname):
        plt.savefig(open('graphs/%s.pdf'%fname, 'wb'), format='pdf')
        plt.clf()
        
        

        
if __name__ == '__main__':
    m = Analyzer()
    conds = [
                    {
                        'type': 'genomic',
                        'status': 'finished',
                        'workload': 1,
                        'deployment': 'standalone'
                    },
                    {
                        'type': 'montage',
                        'status': 'finished',
                        'bandwidth': 100 * 1000 * 1000,
                        'num_of_workers': 5,
                        'workload': 1,
                        'topology': 'intra-rack'
                    }
            ]
    m.analyze(conds, 'worker_size')
    m.save('vm_size')
        
    conds = [{
            'type': 'genomic',
            'status': 'finished',
            'worker_size': 'XOLarge',
            'bandwidth': 100 * 1000 * 1000,
            'num_of_workers': 3,
            'topology': 'intra-rack'
        },
        {
            'type': 'montage',
            'status': 'finished',
            'worker_size': 'XOLarge',
            'bandwidth': 100 * 1000 * 1000,
            'num_of_workers': 5,
            'topology': 'intra-rack'
        }
    ]
    m.analyze(conds, 'workload')
    m.save('workload') 

    conds =[
            {
                'type': 'genomic',
                'status': 'finished',
                'worker_size': 'XOLarge',
                'num_of_workers': 3,
                'workload': 3,
                'topology': 'intra-rack',
            },
            {
                'type': 'montage',
                'status': 'finished',
                'worker_size': 'XOLarge',
                'workload': 1,
                'master_site': 'osf',
                'num_of_workers': 5,
                'topology': 'intra-rack',
            }
        ]
    m.analyze(conds, 'bandwidth')
    m.save('bandwidth')
    
    conds = [
             {
                'type': 'genomic',
                'status': 'finished',
                'worker_size': 'XOLarge',
                'workload': 5,
                'bandwidth': 100 * 1000 * 1000,
                'topology': 'intra-rack'
              },
             {
                'type': 'montage',
                'status': 'finished',
                'worker_size': 'XOLarge',
                'workload': 1,
                'bandwidth': 100 * 1000 * 1000,
                'topology': 'intra-rack',
              }
    ]
    m.analyze(conds, 'num_of_workers')
    m.save('num_of_workers')
#         cond = {
#                 'type': 'genomic',
#                 'status': 'finished',
#                 'workload': 1,
#                 'worker_size': 'XOLarge',
#                 'deployment': 'standalone'
#         }
#         m.get_analysis(cond, 'master_site', asp)
#         m.save('%s-genomic-master' % asp)
#     
#         cond = {
#                 'type': 'montage',
#                 'status': 'finished',
#                 'workload': 1,
#                 'bandwidth': 100 * 1000 * 1000,
#                 'num_of_workers': 5,
#                 'worker_size': 'XOLarge',
#                 'topology': 'intra-rack'
#         }
#         m.get_analysis(cond, 'master_site', asp)
#         m.save('%s-montage-master' % asp)
#             
#         cond = {
#                 'type': 'genomic',
#                 'status': 'finished',
#                 'workload': 1,
#                 'master_site': 'uh',
#                 'worker_size': 'XOLarge',
#                 'deployment': 'standalone'
#         }
#         m.get_analysis(cond, 'daytime', asp)
#         m.save('%s-genomic-daytime' % asp)
#         
#         m.get_analysis(cond, 'weekday', asp)
#         m.save('%s-genomic-weekdays' % asp)
#         
#         cond = {
#                 'type': 'montage',
#                 'status': 'finished',
#                 'topology': 'inter-rack',
#                 'num_of_workers': 4
#                 }
#         m.get_analysis(cond, 'worker_sites', asp)
#         m.save('%s-montage-workers' % asp)
#     
#         cond = {
#                 'type': 'montage',
#                 'status': 'finished',
#                 'bandwidth': 100 * 1000 * 1000,
#                 'topology': 'intra-rack',
#                 'worker_size': 'XOLarge',
#                 'num_of_workers': 5,
#                 'workload': 1,
#                 'master_site': 'wsu',
#         }
#         m.get_analysis(cond, 'daytime', asp)
#         m.save('%s-montage-daytime' % asp)
#         
#         m.get_analysis(cond, 'weekday', asp)
#         m.save('%s-montage-weekdays' % asp)
#     cond = {
#         'exp_id': '0355721a-6098-452b-ab66-ccde2ff2e749'
#     }
#     m.get_analysis(cond, 'cmdline', 'job_cpu')
#     m.save('job_cpu-genomic-cmdline')
 
#     cond = {
#             'type': 'genomic',
#             'status': 'finished',
#             'deployment': 'standalone'
#             }
#     m.get_walltime_by_size(cond)
#     m.save('genomic-size')
