#!/usr/bin/env python

import pymongo, uuid

db = pymongo.MongoClient('localhost', 27017)

db['cluster']['workflow']['manifest'].remove({})
db['cluster']['workflow']['vm_size'].remove({})
db['cluster']['workflow']['type'].remove({})
db['cluster']['workflow']['topology'].remove({})
db['cluster']['workflow']['mode'].remove({})
db['cluster']['workflow']['storage_site'].remove({})
db['cluster']['workflow']['storage_type'].remove({})
db['cluster']['workflow']['site'].remove({})

db['cluster15']['workflow']['manifest'].insert({
    'id': str(uuid.uuid4()),
    'type': 'genomic',
    'mode': 'standalone',
    'storage_site': 'local',
    'storage_type': 'regular',
    'manifest': '\n'.join([l for l in open('./geno-single', 'r')]),
    })
db['cluster15']['workflow']['manifest'].insert({
    'id': str(uuid.uuid4()),
    'type': 'genomic',
    'mode': 'multinode',
    'storage_site': 'remote',
    'storage_type': 'nfs',
    'manifest': '\n'.join([l for l in open('./geno-multi-nfs', 'r')]),
    })
db['cluster15']['workflow']['manifest'].insert({
    'id': str(uuid.uuid4()),
    'type': 'montage',
    'mode': 'multinode',
    'storage_site': 'local',
    'storage_type': 'nfs',
    'manifest': '\n'.join([l for l in open('./montage-multi-nfs', 'r')]),
    })

db['cluster15']['workflow']['type'].insert({
        'name': 'montage',
        'notes': 'a Montage workflow',
        'executables': ['mMakeHdr-3.3', 'mExecTG-3.3', 'mMakeImg-3.3', 'mDAGFiles-3.3', 'mImgtbl-3.3',
            'mAddExec-3.3', 'mTileHdr-3.3', 'mPresentation-3.3', 'mSubset-3.3', 'mGetHdr-3.3',
            'mConvert-3.3', 'mHdrtbl-3.3', 'mAdd-3.3', 'mArchiveList-3.3', 'mExamine-3.3', 
            'mExec-3.3', 'mArchiveGet-3.3', 'mDAG-3.3', 'mFixNaN-3.3', 'mDAGGalacticPlane-3.3', 
            'mBestImage-3.3', 'mTblSort-3.3', 'mQuickSearch-3.3', 'mHdr-3.3', 'mDiffFit-3.3', 
            'mCoverageCheck-3.3', 'mArchiveExec-3.3', 'mConcatFit-3.3', 'mProjectPP-3.3',
            'mNotifyTG-3.3', 'mJPEG-3.3', 'mFlattenExec-3.3', 'mSubimage-3.3', 'mCatMap-3.3',
            'mShrinkHdr-3.3', 'mPutHdr-3.3', 'mDiffFitExec-3.3', 'mGridExec-3.3', 
            'mHdrCheck-3.3', 'mFixHdr-3.3', 'mPix2Coord-3.3', 'mTileImage-3.3', 'mDiff-3.3', 'mFitplane-3.3',
            'mShrink-3.3', 'mRotate-3.3', 'mDAGTbls-3.3', 'mBgExec-3.3', 'mFitExec-3.3', 'mNotify-3.3',
            'mDiffExec-3.3', 'mTblExec-3.3', 'mBackground-3.3', 'mOverlaps-3.3', 'mBgModel-3.3', 'mProjExec-3.3',
            'mProject-3.3', 'mTANHdr-3.3'],
    })

db['cluster15']['workflow']['type'].insert({
        'name': 'genomic',
        'notes': 'a genomic sequencing workflow',
        'executables': ['bwa', 'picard', 'gatk', 'samtools'], 
    })

db['cluster15']['workflow']['vm_size'].insert({
    'name': 'bare-metal',
    'value': 'ExoGENI-M4',
    'cores': 16,
    'ram': 48,
    'disk': 600
    })

db['cluster15']['workflow']['vm_size'].insert({
    'name': 'small',
    'value': 'XOSmall',
    'cores': 1,
    'ram': 1,
    'disk': 10
    })
db['cluster15']['workflow']['vm_size'].insert({
    'name': 'medium',
    'value': 'XOMedium',
    'cores': 1,
    'ram': 3,
    'disk': 25
    })
db['cluster15']['workflow']['vm_size'].insert({
    'name': 'large',
    'value': 'XOLarge',
    'cores': 2,
    'ram': 6,
    'disk': 50
    })
db['cluster15']['workflow']['vm_size'].insert({
    'name': 'extra-large',
    'value': 'XOXlarge',
    'cores': 4,
    'ram': 12,
    'disk': 75
    })

db['cluster15']['workflow']['topology'].insert({
    'name': 'inter-rack'
    })
db['cluster15']['workflow']['topology'].insert({
    'name': 'intra-rack'
    })

db['cluster15']['workflow']['mode'].insert({
    'name': 'standalone'
    })
db['cluster15']['workflow']['mode'].insert({
    'name': 'multinode'
    })

db['cluster15']['workflow']['storage_site'].insert({
    'name': 'local'
    })
db['cluster15']['workflow']['storage_site'].insert({
    'name': 'remote'
    })
db['cluster15']['workflow']['storage_type'].insert({
    'name': 'regular'
    })
db['cluster15']['workflow']['storage_type'].insert({
    'name': 'nfs'
    })


db['cluster15']['workflow']['site'].insert([
    {'name': 'rci', 'location': 'Chapel Hill, NC'},
    {'name': 'bbn', 'location': 'Boston, MA'},
    {'name': 'fiu', 'location': 'Miami, FL'},
    {'name': 'uh', 'location': 'Houston, TX'},
    {'name': 'ufl', 'location': 'Gainesville, FL'},
    {'name': 'osf', 'location': 'Oakland, CA'},
    {'name': 'sl', 'location': 'Chicago, IL'},
    {'name': 'ucd', 'location': 'Davis, CA'},
    {'name': 'wvn', 'location': 'Morgantown, WV'},
    {'name': 'tamu', 'location': 'College Station, TX'},
    ])
