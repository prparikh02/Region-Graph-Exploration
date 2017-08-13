import json
import pymongo
import os
import time
from pymongo import MongoClient


def mongo_connect():
    client = MongoClient('localhost', 27017)
    db = client['danish_project']
    coll = db['articles']
    return coll


if __name__ == '__main__':
    coll = mongo_connect()

    directory = '/home/parth/Desktop/Abello/Danish_Project/FT/'
    for filename in os.listdir(directory):
        if not filename.endswith('.json'):
            continue
        t0 = time.time()
        with open(directory + filename, 'r') as f:
            articles = json.load(f)
        coll.insert_many(articles)
        t1 = time.time()
        print('time elapsed: {} for file: {}'.format(t1 - t0, filename))
