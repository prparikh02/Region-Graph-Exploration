import cPickle as pickle
import json
import pymongo
import time
from argparse import ArgumentParser, RawTextHelpFormatter
from pymongo import MongoClient


def init_argparser():
    description = ('Update element associations in MongoDB')
    parser = ArgumentParser(description=description,
                            formatter_class=RawTextHelpFormatter)

    parser.add_argument('input_file', metavar='element_associations',
                        type=str, help='path to pickled regions file')

    parser.add_argument('database_name', metavar='db', type=str,
                        help='name of existing or new Mongo database')

    return parser


def mongo_connect(db_name):
    client = MongoClient('localhost', 27017)
    db = client[db_name]
    collection = db['elements']
    return collection


if __name__ == '__main__':
    parser = init_argparser()
    args = parser.parse_args()

    input_file = args.input_file
    db_name = args.database_name

    with open(input_file, 'rb') as f:
        elem_assoc = pickle.load(f)

    collection = mongo_connect(db_name)
    for element_id, set_ids in elem_assoc.iteritems():
        collection.update({'_id': element_id},
                          {'$set': {'associations': list(set_ids)}})
