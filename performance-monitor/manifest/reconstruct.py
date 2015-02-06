'''
Created on Feb 3, 2015

@author: dc
'''
import os
import pymongo

if __name__ == '__main__':
    db = pymongo.MongoClient()
    
    db['cluster15']['workflow']['mode'].drop()
    db['cluster15']['workflow']['storage_site'].drop()
    db['cluster15']['workflow']['storage_type'].drop()
    db['cluster15']['workflow']['manifest'].drop()
     
    # workflow.image
    img = db['cluster15']['workflow']['image']
    images = [i for i in img.find({}, {'_id': 0})]
    wf = db['cluster15']['workflow']['type']
     
    for i in images:
        wf.update({'name': i['name']}, {'$set': {'image': {
                                                            'uri': i['uri'],
                                                            'guid': i['guid'],
                                                            }}})
    img.drop()
    
    # workflow manifest
    wf.update({'name': 'genomic'}, {'$set': {'postscript': {
                                                            'master': os.linesep.join([l for l in open('geno_master.sh', 'r')]),
                                                            'worker': os.linesep.join([l for l in open('geno_worker.sh', 'r')]),
                                                            }}})
    wf.update({'name': 'montage'}, {'$set': {'postscript': {
                                                            'master': os.linesep.join([l for l in open('montage_master.sh', 'r')]),
                                                            'worker': os.linesep.join([l for l in open('montage_worker.sh', 'r')]),
                                                            }}})
    # workflow.experiment
    exp = db['cluster15']['workflow']['experiment']
    res = [e for e in exp.find({}, {'_id': 0})]
    for e in res:
        try:
            e['workload'] = int(e['run_num'])
            del e['run_num']
            e['deployment'] = e['mode']
            del e['mode']
            e['filesystem'] = e['storage_type']
            e['storage_type'] = e['storage_site']
            del e['storage_site']
            e['reservation'] = int(e['reservation'])
            if not e['storage_size'] or not len(e['storage_size']):
                del e['storage_size']
            else:
                e['storage_size'] = int(e['storage_size'])
            if not e['bandwidth']:
                del e['bandwidth']
            e['num_of_workers'] = 0
            if 'worker_sites' not in e:
                e['worker_sites'] = [{'site': e['master_site'], 'num': 1}]
            for i in e['worker_sites']:
                i['num'] = int(i['num'])
                e['num_of_workers'] += i['num']
            exp.remove({'exp_id': e['exp_id']})
            exp.insert(e)
        except KeyError:
            print e['exp_id']
    
    # experiment.run
    run = db['cluster15']['experiment']['run']
    runs = [r for r in run.find({}, {'_id': 0})]
    for r in runs:
        r['timestamp'] = int(r['timestamp'])
        r['walltime'] = int(r['walltime'])
        db['cluster15']['workflow']['experiment'].update({'exp_id': r['exp_id']}, {'$set': {'last_update_time': r['timestamp']}})
        run.remove({'run_id': r['run_id'], 'exp_id': r['exp_id']})
        run.insert(r)
    exp = db['cluster15']['workflow']['experiment']
    exps = [e for e in exp.find({}, {'_id': 0})]
    for e in exps:
        if 'last_update_time' not in e:
            exp.update({'exp_id': e['exp_id']}, {'$set': {'last_update_time': int(e['create_time'])}})

