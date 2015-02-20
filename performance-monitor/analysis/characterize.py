'''
Created on 2015/02/18

@author: dc
'''
import re
import pymongo
import time
import numpy
import matplotlib
import matplotlib.pyplot as plt

from matplotlib.pyplot import legend, title

# matplotlib global settings
matplotlib.rc('font', size=10)
matplotlib.rc('legend', fontsize=10, frameon=False)

montage_jobs = ['mProjectPP', 'mDiffFit', 'mConcatFit', 'mBgModel',  'mBackground', 'mImgtbl', 'mAdd', 'mShrink', 'mJPEG']
def categorize(wf, data, aspect):
    cat = dict()
    for d in data:
        parts = d['name'].split('_')
        if  parts[0] in ['clean', 'stage', 'create', 'cleanup']: 
            continue
        if wf == 'genomic':
            name = re.sub(r'([a-z]+)_ID0+([1-9][0-9]*)', r'\1_\2', d['name'])
        elif wf == 'montage':
            if parts[0] == 'merge':
                name = parts[1].split('-')[0]
            else:
                name = parts[0]
        if name in cat:
            cat[name].append(d[aspect])
        else:
            cat[name] = [d[aspect]]
    for k in cat:
        cat[k] = numpy.average(cat[k])
    return cat
if __name__ == '__main__':
    db = pymongo.MongoClient()
    exp_repo = db['cluster15']['workflow']['experiment']
    job_repo = db['cluster15']['experiment']['job']
    ts = int(time.mktime(time.strptime('2015-02-17 14:00:00', '%Y-%m-%d %H:%M:%S')))
    geno_ids = [e['exp_id'] for e in exp_repo.find({
                                                    'type': 'genomic',
                                                    'status': 'finished',
                                                    'last_update_time': {'$gt': ts}
                                                    }, {'_id': 0, 'exp_id': 1})]
    geno_data = [j for j in job_repo.find({'exp_id': {'$in': geno_ids}}, {'_id': 0}) if 'name' in j]
    
    mon_ids  = [e['exp_id'] for e in exp_repo.find({'type': 'montage', 
                                                          'status': 'finished',
                                                          'last_update_time': {'$gt':   ts}}, {'_id': 0, 'exp_id': 1})]
    mon_data = [ j for j in job_repo.find({'exp_id': {'$in': mon_ids}}, {'_id': 0})]
    geno_cpu_pct = categorize('genomic', geno_data, 'avg_cpu_percent')
    geno_mem_pct = categorize('genomic', geno_data, 'avg_mem_percent')
    geno_rrate = categorize('genomic', geno_data, 'read_rate')
    geno_wrate = categorize('genomic', geno_data, 'write_rate')
    mon_cpu_pct= categorize('montage', mon_data, 'avg_cpu_percent')
    mon_mem_pct = categorize('montage', mon_data, 'avg_mem_percent')
    mon_rrate = categorize('montage', mon_data, 'read_rate')
    mon_wrate = categorize('montage', mon_data, 'write_rate')
    
    fig = plt.figure(1)
   
    ax = plt.subplot(211)
    tags = sorted(geno_cpu_pct.keys(), key=lambda e: int(re.sub('[^0-9]', '', e)))
    x = range(0, len(tags))
    
    l1, = ax .plot(x, [geno_cpu_pct[k] for k in geno_cpu_pct], 'r<-', markersize=5, label='CPU util.')
    l2, = ax.plot(x, [geno_mem_pct[k] for k in geno_mem_pct], 'b>-', markersize=5, label='Memory util.')
    
    ax2 = ax.twinx()
    l3, = ax2.plot(x, [geno_rrate[k] / (1024 * 1024) for k in geno_rrate], 'gD--' , markersize=5, label='Read rate')
    l4, = ax2.plot(x, [geno_wrate[k] / (1024 * 1024) for k in geno_wrate], 'ms--' , markersize=5, label='Write rate')
    ax2.set_ylabel('I/O Rate(MB/s)')

    ax.set_ylim(0, ax.get_ylim()[1]  * 1.1)
    ax.set_ylabel('Utilization(%)')    
    ax.set_xlim(0, len(tags) - 1)
    ax.set_xticks(x)
    ax.set_xticklabels(tags, rotation=40)
    title('Exomic alignment workflow')
    
    ax3 = plt.subplot(212)
    tags = sorted(mon_cpu_pct.keys(), key=montage_jobs.index)
    x = range(0, len(tags))

    l1, = ax3.plot(x, [mon_cpu_pct[k] for k in mon_cpu_pct], 'r<-', markersize=5, label='CPU util.')
    l2, = ax3.plot(x, [mon_mem_pct[k] for k in mon_mem_pct], 'b>-', markersize=5, label='Memory util.')

    ax4 = ax3.twinx()
    l3, = ax4.plot(x, [mon_rrate[k] / (1024 * 1024) for k in mon_rrate], 'gD--' , markersize=5, label='Read rate')
    l4, = ax4.plot(x, [mon_wrate[k] / (1024 * 1024) for k in mon_wrate], 'ms--' , markersize=5, label='Write rate')
    ax4.set_ylabel('I/O Rate(MB/s)')

    ax3.set_ylim(0, ax3.get_ylim()[1]  * 1.1)
    ax3.set_ylabel('Utilization(%)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(tags, rotation=40)
    title('Montage workflow')

    legend(bbox_to_anchor=(0, -0.5, 1, 0.102), loc=9, ncol=4, mode='expand', borderaxespad=0, handles=[l1, l2, l3, l4])
    plt.tight_layout(h_pad=0.15)
    plt.subplots_adjust(bottom=0.2 )
    plt.savefig(open('graphs/characterization.pdf', 'wb'), format='pdf')
    