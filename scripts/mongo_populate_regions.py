import cPickle as pickle
import json
import pymongo
import time
from argparse import ArgumentParser, RawTextHelpFormatter
from pymongo import MongoClient


def init_argparser():
    description = ('Load regions into MongoDB')
    parser = ArgumentParser(description=description,
                            formatter_class=RawTextHelpFormatter)

    parser.add_argument('input_file', metavar='regions', type=str,
                        help='path to pickled regions file')

    parser.add_argument('database_name', metavar='db', type=str,
                        help='name of existing or new Mongo database')

    return parser


def mongo_connect(db_name):
    client = MongoClient('localhost', 27017)
    db = client[db_name]
    collection = db['regions']
    return collection


if __name__ == '__main__':
    parser = init_argparser()
    args = parser.parse_args()

    input_file = args.input_file
    db_name = args.database_name

    with open(input_file, 'rb') as f:
        regions = pickle.load(f)

    collection = mongo_connect(db_name)
    A = []
    for region_id, info in regions.iteritems():
        A.append({
            '_id': region_id,
            'depth': len(info['sets']),
            'size': len(info['elems']),
            'elements': {e: 0 for e in info['elems']},
            'sets': {s: 0 for s in info['sets']},
        })
    collection.insert_many(A)
