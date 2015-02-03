'''
Created on Feb 3, 2015

@author: dc
'''
import pymongo

if __name__ == '__main__':
    db = pymongo.MongoClient()
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
            print e
            exp.remove({'exp_id': e['exp_id']})
            exp.insert(e)
        except KeyError:
            print e['exp_id']

