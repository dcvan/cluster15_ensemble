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
time_period = ['0-3', '4-7', '8-11', '12-15', '16-19', '20-23']
weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
racks = ['rci', 'bbn', 'fiu', 'uh', 'tamu', 'wsu', 'ucd', 'sl', 'ufl', 'uva']

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
            e[sortby] = time.strftime('%H' if sortby == 'daytime' else '%a', time.localtime(e['last_update_time']))
    elif sortby == 'worker_sites':
        sortby = 'overlap'
        for e in exps:
            e['worker_sites'] = [s['site'] for s in e['worker_sites']]
        caliber = set([u'ufl', u'fiu', u'wvn', u'osf'])
        for e in exps:
            print set(e['worker_sites'])
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
    elif sortby == 'daytime':
        for h in time_period:
            cat[h] = []
    elif sortby == 'weekday':
        for w in weekdays:
            cat[w] = []
    elif sortby == 'master_site':
        for s in racks:
            cat[s] = []
    elif sortby == 'overlap':
        for i in range(0, 5):
            cat[i] = []
    for e in exps:
        if sortby == 'bandwidth':
            cat[e[0] / (1000 * 1000)].append(e[1])
        elif sortby == 'daytime':
            k = time_period[int(e[0])/4]
            cat[k].append(e[1])
        elif sortby == 'master_site':
            if e[0] in racks:
                cat[e[0]].append(e[1])
        else:
            cat[e[0]].append(e[1])
    return cat 
    
class Analyzer:

    def analyze(self, conds, sortby):
        labels = ['Exomic', 'Montage']
        styles = ['rD-', 'b^--']
        cat = [get_experiments(c, sortby) for c in conds]
        if sortby in ['worker_size']:
            tags = sorted(cat[0].keys(), key=vm_sizes.index)
        elif sortby in ['master_site']:
            tags = sorted(cat[0].keys(), key=racks.index)
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
        elif sortby =='master_site':
            ax1.set_ylim(90, 100)
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
        
    def analyze_vary_time(self, conds):
        styles = ['rD-', 'c<--', 'bH-', 'y>--']
        labels = ['Exomic - time', 'Exomic - day', 'Montage - time', 'Montage - day']
        cat = (
               [get_experiments(cond[0], 'daytime'), get_experiments(cond[0], 'weekday')],
               [get_experiments(cond[1], 'daytime'), get_experiments(cond[1], 'weekday')]
        )
        # get tag
        d_tags = time_period
        w_tags = weekdays
        
        # get data
        g_d_wt_raw, g_d_sys_raw, g_w_wt_raw, g_w_sys_raw = {}, {}, {}, {}
        m_d_wt_raw, m_d_sys_raw, m_w_wt_raw, m_w_sys_raw = {}, {}, {}, {}
        for d in d_tags:
            g_d_wt_raw[d] = [r['walltime'] for r in run_handle.find({'exp_id': {'$in': cat[0][0][d]}}, {'_id': 0, 'walltime': 1})]
            g_d_sys_raw[d] = [s for s in sys_handle.find({'exp_id': {'$in': cat[0][0][d]}}, {'_id': 0})]
            m_d_wt_raw[d] = [r['walltime'] for r in run_handle.find({'exp_id': {'$in': cat[1][0][d]}}, {'_id': 0, 'walltime': 1})]
            m_d_sys_raw[d] = [s for s in sys_handle.find({'exp_id': {'$in': cat[1][0][d]}}, {'_id': 0})]
        for w in w_tags:
            g_w_wt_raw[w] = [r['walltime'] for r in run_handle.find({'exp_id': {'$in': cat[0][1][w]}}, {'_id': 0, 'walltime': 1})]
            g_w_sys_raw[w] = [s for s in sys_handle.find({'exp_id': {'$in': cat[0][1][w]}}, {'_id': 0})]
            m_w_wt_raw[w] = [r['walltime'] for r in run_handle.find({'exp_id': {'$in': cat[1][1][w]}}, {'_id': 0, 'walltime': 1})]
            m_w_sys_raw[w] = [s for s in sys_handle.find({'exp_id': {'$in': cat[1][1][w]}}, {'_id': 0})]
        
        # get xticks counter
        xd, xw = range(0, len(d_tags)), range(0, len(w_tags))
        
        # plot
        plt.figure()
        
        # walltime
        ax0_d = plt.subplot(321)
        ax0_d.plot(xd, [numpy.average(g_d_wt_raw[d]) if g_d_wt_raw[d] else None for d in d_tags], styles[0], markersize=5, label=labels[0])
        ax0_d.plot(xd, [numpy.average(m_d_wt_raw[d]) if m_d_wt_raw[d] else None for d in d_tags], styles[2], markersize=5, label=labels[2])
        ax0_d.set_xticks(xd)
        ax0_d.set_xticklabels(d_tags)
        ax0_d.set_ylabel('Walltime(min.)')
        
        ax0_w = ax0_d.twiny()
        ax0_w.plot(xw, [numpy.average(g_w_wt_raw[w]) if g_w_wt_raw[w] else None for w in w_tags], styles[1], markersize=5, label=labels[1])
        ax0_w.plot(xw, [numpy.average(m_w_wt_raw[w]) if m_w_wt_raw[w] else None for w in w_tags], styles[3], markersize=5, label=labels[3])
        ax0_w.set_xticks(xw)
        ax0_w.set_xticklabels(w_tags)
        
        # cpu usage
        ax1_d = plt.subplot(322)
        ax1_d.plot(xd, [numpy.average([s['sys_cpu_percent'] for s in g_d_sys_raw[d]]) if g_d_sys_raw[d] else None for d in d_tags], styles[0], markersize=5, label=labels[0])
        ax1_d.plot(xd, [numpy.average([s['sys_cpu_percent'] for s in m_d_sys_raw[d]]) if m_d_sys_raw[d] else None for d in d_tags], styles[2], markersize=5, label=labels[2])
        ax1_d.set_xticks(xd)
        ax1_d.set_xticklabels(d_tags)
        ax1_d.set_ylabel('CPU util.(%)')
        
        ax1_w = ax1_d.twiny()
        ax1_w.plot(xw, [numpy.average([s['sys_cpu_percent'] for s in g_w_sys_raw[w]]) if g_w_sys_raw[w] else None for w in w_tags], styles[1], markersize=5, label=labels[1])
        ax1_w.plot(xw, [numpy.average([s['sys_cpu_percent'] for s in m_w_sys_raw[w]]) if m_w_sys_raw[w] else None for w in w_tags], styles[3], markersize=5, label=labels[3])
        ax1_w.set_xticks(xw)
        ax1_w.set_xticklabels(w_tags)
        ax1_w.set_ylim(95, 100)
        
        # memory usage
        ax2_d = plt.subplot(323)
        ax2_d.plot(xd, [numpy.average([s['sys_mem_percent'] for s in g_d_sys_raw[d]]) if g_d_sys_raw[d] else None for d in d_tags], styles[0], markersize=5, label=labels[0])
        ax2_d.plot(xd, [numpy.average([s['sys_mem_percent'] for s in m_d_sys_raw[d]]) if m_d_sys_raw[d] else None for d in d_tags], styles[2], markersize=5, label=labels[2])
        ax2_d.set_xticks(xd)
        ax2_d.set_xticklabels(d_tags)
        ax2_d.set_ylabel('Memory util.(%)')
        
        ax2_w = ax2_d.twiny()
        ax2_w.plot(xw, [numpy.average([s['sys_mem_percent'] for s in g_w_sys_raw[w]]) if g_w_sys_raw[w] else None for w in w_tags], styles[1], markersize=5, label=labels[1])
        ax2_w.plot(xw, [numpy.average([s['sys_mem_percent'] for s in m_w_sys_raw[w]]) if m_w_sys_raw[w] else None for w in w_tags], styles[3], markersize=5, label=labels[3])
        ax2_w.set_xticks(xw)
        ax2_w.set_xticklabels(w_tags)
        
        # read rate
        ax3_d = plt.subplot(324)
        ax3_d.plot(xd, [numpy.average([s['sys_read_rate'] / (1024 * 1024) for s in g_d_sys_raw[d]]) if g_d_sys_raw[d] else None for d in d_tags], styles[0], markersize=5, label=labels[0])
        ax3_d.plot(xd, [numpy.average([s['sys_read_rate'] / (1024 * 1024) for s in m_d_sys_raw[d]]) if m_d_sys_raw[d] else None for d in d_tags], styles[2], markersize=5, label=labels[2])
        ax3_d.set_xticks(xd)
        ax3_d.set_xticklabels(d_tags)
        ax3_d.set_ylabel('Read rate (MB/s)')
        
        ax3_w = ax3_d.twiny()
        ax3_w.plot(xw, [numpy.average([s['sys_read_rate'] / (1024 * 1024) for s in g_w_sys_raw[w]]) if g_w_sys_raw[w] else None for w in w_tags], styles[1], markersize=5, label=labels[1])
        ax3_w.plot(xw, [numpy.average([s['sys_read_rate'] / (1024 * 1024) for s in m_w_sys_raw[w]]) if m_w_sys_raw[w] else None for w in w_tags], styles[3], markersize=5, label=labels[3])
        ax3_w.set_xticks(xw)
        ax3_w.set_xticklabels(w_tags)
        
        # write rate
        ax4_d = plt.subplot(325)
        l1, = ax4_d.plot(xd, [numpy.average([s['sys_write_rate'] / (1024 * 1024) for s in g_d_sys_raw[d]]) if g_d_sys_raw[d] else None for d in d_tags], styles[0], markersize=5, label=labels[0])
        l3, = ax4_d.plot(xd, [numpy.average([s['sys_write_rate'] / (1024 * 1024) for s in m_d_sys_raw[d]]) if m_d_sys_raw[d] else None for d in d_tags], styles[2], markersize=5, label=labels[2])
        ax4_d.set_xticks(xd)
        ax4_d.set_xticklabels(d_tags)
        ax4_d.set_ylabel('Write rate (MB/s)')
        
        ax4_w = ax4_d.twiny()
        l2, = ax4_w.plot(xw, [numpy.average([s['sys_write_rate'] / (1024 * 1024) for s in g_w_sys_raw[w]]) if g_w_sys_raw[w] else None for w in w_tags], styles[1], markersize=5, label=labels[1])
        l4, = ax4_w.plot(xw, [numpy.average([s['sys_write_rate'] / (1024 * 1024) for s in m_w_sys_raw[w]]) if m_w_sys_raw[w] else None for w in w_tags], styles[3], markersize=5, label=labels[3])
        ax4_w.set_xticks(xw)
        ax4_w.set_xticklabels(w_tags)
        ax4_w.set_ylim(0, 30)
        
        legend(bbox_to_anchor=(1.45, 0.6), loc=2, ncol=1, borderaxespad=0, borderpad=0.7, labelspacing=1, handlelength=3, handles=[l1, l2, l3, l4], fontsize=8)
        plt.tight_layout()

        
    def analyze_varying_intersite(self, cond):
        '''
        
        '''
        styles = ['rD-', 'b^--']
        cat = get_experiments(cond, 'worker_sites')
        print [len(cat[d]) for d in cat]
        tags = cat.keys()
        tags.sort()
        wt_raw, sys_raw = {}, {}
        for group in tags:
            wt_raw[group] = [d['walltime'] for d in run_handle.find({'exp_id': {'$in': cat[group]}}, {'_id': 0, 'walltime': 1})]
            sys_raw[group] = [d for d in sys_handle.find({'exp_id': {'$in': cat[group]}}, {'_id': 0})]
        x = range(0, len(tags))
        
        #walltime
        plt.figure(1)
        ax0 = plt.subplot(311)
        ax0.plot(x, [numpy.average(wt_raw[k]) if wt_raw[k] else None for k in tags], styles[0], markersize=5)
        ax0.set_xticks(x)
        ax0.set_xticklabels(tags)
        ax0.set_ylim(100, 210)
        ax0.set_ylabel('Walltime(mins)')
        
        #cpu 
        ax1 = plt.subplot(312)
        l1, = ax1.plot(x, [numpy.average([d['sys_cpu_percent'] for d in sys_raw[k]]) if sys_raw[k] else None for k in tags], styles[0], markersize=5, label='CPU')
        l2, = ax1.plot(x, [numpy.average([d['sys_mem_percent'] for d in sys_raw[k]]) if sys_raw[k] else None for k in tags], styles[1], markersize=5, label='Memory')
        ax1.legend(handles=[l1, l2], fontsize=8, loc=2, ncol=2, frameon=False)
        ax1.set_xticks(x)
        ax1.set_xticklabels(tags)
        ax1.set_ylim(ymax=105)
        ax1.set_ylabel('Utilization.(%)')

        #read rate
        ax3 = plt.subplot(313)
        l1, =ax3.plot(x, [numpy.average([d['sys_read_rate'] / (1024 * 1024) for d in sys_raw[k]]) if sys_raw[k] else None for k in tags], styles[0], markersize=5, label='Read')
        l2, = ax3.plot(x, [numpy.average([d['sys_write_rate'] / (1024 * 1024) for d in sys_raw[k]]) if sys_raw[k] else None for k in tags], styles[1], markersize=5, label='Write')
        ax3.legend(handles=[l1, l2], fontsize=8, loc=2, ncol=2, frameon=False)
        ax3.set_xticks(x)
        ax3.set_xticklabels(tags)
#         ax3.set_ylim(3, 6)
        ax3.set_ylim(ymin=2)
        ax3.set_ylabel('I/O rate(MB/s)')
        
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
    cond = [{
            'type': 'genomic',
            'status': 'finished',
            'workload': 1,
            'worker_size': 'XOLarge',
            'deployment': 'standalone'
    },
    {
            'type': 'montage',
            'status': 'finished',
            'workload': 1,
            'bandwidth': 100 * 1000 * 1000,
            'num_of_workers': 5,
            'worker_size': 'XOLarge',
            'topology': 'intra-rack'
    }]
    m.analyze(cond, 'master_site')
    m.save('intrasite')

#         
    cond = {
            'type': 'montage',
            'status': 'finished',
            'topology': 'inter-rack',
            'num_of_workers': 4
            }
    m.analyze_varying_intersite(cond)
    m.save('interrack')
     
    cond = [{
            'type': 'genomic',
            'status': 'finished',
            'workload': 1,
            'master_site': 'uh',
            'worker_size': 'XOLarge',
            'deployment': 'standalone'
    },
    {
            'type': 'montage',
            'status': 'finished',
            'bandwidth': 100 * 1000 * 1000,
            'topology': 'intra-rack',
            'worker_size': 'XOLarge',
            'num_of_workers': 5,
            'workload': 1,
            'master_site': 'wsu',
    }
    ]
    m.analyze_vary_time(cond)
    m.save('time')
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
