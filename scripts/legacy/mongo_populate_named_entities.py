import cPickle as pickle
import json
import pymongo
import time
from pymongo import MongoClient


def mongo_connect():
    client = MongoClient('localhost', 27017)
    db = client['danish_project']
    coll = db['named_entities_1991']
    return coll


if __name__ == '__main__':
    coll = mongo_connect()

    with open('./scripts/ner_index_1991.pkl', 'rb') as f:
        named_entities = pickle.load(f)

    A = []
    for ne, info in named_entities.iteritems():
        A.append({
            '_id': info['_id'],
            'articles': {a: 0 for a in info['articles']},
            'named_entity': ne
        })
    coll.insert_many(A)
