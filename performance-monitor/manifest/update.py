import pymongo

db = pymongo.MongoClient()
db['cluster15']['workflow']['manifest'].update({}, {'$unset': {'manifest': 1}}, multi=True)
db['cluster15']['workflow']['manifest'].update(
        {'type': 'genomic', 'mode': 'multinode'},
        {'$set': {
            'master_postscript': '\n'.join([l for l in open('geno_master.sh', 'r')]),
            'worker_postscript': '\n'.join([l for l in open('geno_worker.sh', 'r')]),
            }})
db['cluster15']['workflow']['manifest'].update(
        {'type': 'montage'},
        {'$set': {
            'master_postscript': '\n'.join([l for l in open('montage_master.sh', 'r')]),
            'worker_postscript': '\n'.join([l for l in open('montage_worker.sh', 'r')]),
            }})
db['cluster15']['workflow']['manifest'].update(
        {'type':'genomic', 'mode': 'standalone'},
        {'$set': {
            'master_postscript': '\n'.join([l for l in open('geno_single.sh', 'r')])
            }})
db['cluster15']['workflow']['template'].update({'name': 'manifest'}, 
    {'$set': {'value': '\n'.join([l for l in open('golden-copy.xml', 'r')])}},
    upsert=True)
db['cluster15']['workflow']['image'].insert({
        'name': 'genomic', 
        'uri': 'http://geni-images.renci.org/images/claris/genopegirods/geno-peg-irods.xml',
        'guid': '076e6834f5c7ebd9eb1ecf481e72ef0befed8eb5'
        })
db['cluster15']['workflow']['image'].insert({
        'name': 'montage',
        'uri': 'http://geni-images.renci.org/images/pruth/ADAMANT/montage.v2.0.7a.xml',
        'guid': 'f140b31d8257282f08714b6bc94b03abc8a74859'
    })
