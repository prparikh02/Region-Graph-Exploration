import cPickle as pickle
import json
import pymongo
import time
from pymongo import MongoClient


def mongo_connect():
    client = MongoClient('localhost', 27017)
    db = client['danish_project']
    coll = db['regions_1991']
    return coll


if __name__ == '__main__':
    coll = mongo_connect()

    with open('./scripts/regions_1991.pkl', 'rb') as f:
        regions = pickle.load(f)

    A = []
    for region, info in regions.iteritems():
        A.append({
            '_id': region,
            'named_entities': {a: 0 for a in info['elems']},
            'depth': len(info['sets']),
            'size': len(info['elems'])
        })
    coll.insert_many(A)
