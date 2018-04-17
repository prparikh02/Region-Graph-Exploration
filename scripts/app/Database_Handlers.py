import json
from pymongo import MongoClient
"""Database Handlers

This module provides functions that handle all interaction with MongoDB.

There are currently several blocks of code that do the same thing, but with
legacy database schema.

TODO:
    * Migrate all databases with legacy schema to the current, generic format.
    * Abstract the logic of these functions to remove redundant functions.
"""

# These globals define the database and collections to be accessed
client = MongoClient('localhost', 27017)

"""Legacy CiteseerX format
TODO: Deprecate
"""
# db = client['citeseerx']
# clusters_coll = db['clusters']
# paper_md_coll = db['paper_metadata']

"""Legacy Named Entity format
TODO: Deprecate
"""
db = client['danish_project']
named_entities_coll = db['named_entities_1991']
regions_coll = db['regions_1991']

"""Current, generic format"""
# db = client['study_plan']
# elements_coll = db['elements']
# regions_coll = db['regions']


def landmark_regions(clusters):
    """Gets landmark regions and each of their intra-cluster regions.

    Args:
        clusters (dict): An object whose key is a cluster id and whose value is
                         another object containing a list of regions in that
                         cluster, and the landmark of the cluster.

    Returns:
        A dict with landmark_id as key and a list of elements associated with
        that landmark region as the value.
    """
    # =========================
    # NOTE: REGION GRAPHS
    response = {}
    for group_id, group_data in clusters.iteritems():
        landmark_id = group_data['landmark']['id']
        region_cursor = regions_coll.find({'_id': landmark_id})
        # TODO: Should be an assertion that region_cursor is of length 1
        region = region_cursor[0]

        # =========================
        # BEGIN SPECIFIC CODE --> Named Entity Graph
        named_entities = []
        for ne_id in region['named_entities']:
            named_entities_cursor = \
                named_entities_coll.find({'_id': int(ne_id)})
            for named_entity in named_entities_cursor:
                named_entities.append(named_entity['named_entity'])
        response[landmark_id] = ' | '.join(named_entities)
        # =========================

        # =========================
        # NOTE: GENERIC
        #       This should be the eventual generic code for all region graphs
        # elements = []
        # for elem_id in region['elements']:
        #     elements_cursor = elements_coll.find({'_id': elem_id})
        #     for elem in elements_cursor:
        #         elements.append(elem['content'])
        # response[landmark_id] = ' | '.join([str(e) for e in elements])
        # =========================
    # =========================

    # =========================
    # # NOTE: CITESEERX
    # response = {}
    # # NOTE: clusters not to be confused with clusters in citeseerx database
    # for group_id, group_data in clusters.iteritems():
    #     landmark = group_data['landmark']
    #     cluster_id = landmark['label']

    #     cursor = clusters_coll.find({'cluster_id': cluster_id})
    #     dois = [doc['doi'] for doc in cursor]
    #     if not dois:
    #         resposne[cluster_id] = ''
    #         continue

    #     cursor = paper_md_coll.find({'doi': {'$in': dois}})
    #     # NOTE: remove [0:1] from cursor to show all results
    #     for doc in cursor[0:1]:
    #         response[cluster_id] = doc['title']
    # =========================

    return response


def intracluster_summary(nodes):
    """Gets a list of regions associated with a landmark region, inclusive.

    Args:
        nodes (list): A list of region_id's.

    Returns:
        A dict with region_id as key and a list of elements associated with
        that landmark region as the value.
        TODO: For legacy purposes, the return response is wrapped in another
              dict as the value to a key named 'nodes'. Action item is to
              remove the need for this legacy compatibility.
    """
    # =========================
    # NOTE: REGION GRAPHS
    response = {}
    for node in nodes:
        # FIXME: should this really be node['id'] ?
        region_id = node['label']
        region_cursor = regions_coll.find({'_id': int(region_id)})
        # TODO: Should be an assertion that region_cursor is of length 1
        region = region_cursor[0]

        # =========================
        # BEGIN SPECIFIC CODE --> Named Entity Graph
        named_entities = []
        for ne_id in region['named_entities']:
            named_entities_cursor = \
                named_entities_coll.find({'_id': int(ne_id)})
            for named_entity in named_entities_cursor:
                named_entities.append(named_entity['named_entity'])
        response[region_id] = ' | '.join(named_entities)
        # =========================

        # =========================
        # TODO: GENERIC
        #       This should be the eventual generic code for all region graphs
        # elements = []
        # for elem_id in region['elements']:
        #     elements_cursor = elements_coll.find({'_id': elem_id})
        #     for elem in elements_cursor:
        #         elements.append(elem['content'])
        # response[region_id] = ' | '.join([str(e) for e in elements])
        # =========================
    # =========================

    # =========================
    # # NOTE: CITESEERX
    # response = {}
    # for node in nodes:
    #     cluster_id = node['label']

    #     cursor = clusters_coll.find({'cluster_id': cluster_id})
    #     dois = [doc['doi'] for doc in cursor]
    #     if not dois:
    #         result[cluster_id] = ''
    #         continue

    #     cursor = paper_md_coll.find({'doi': {'$in': dois}})
    #     # NOTE: Remove [0:1] from cursor to show all results
    #     for doc in cursor[0:1]:
    #         response[cluster_id] = doc['title']
    # =========================

    response = {'nodes': response}

    # try:
    #     text_list = [response['nodes'][label] for label in response['nodes']]
    #     summary = gensim.summarization.summarize('. '.join(text_list))
    #     response['summary'] = summary
    # except TypeError, ValueError:
    #     print('could not produce summary...')

    return response


def doc_lookup(node_id):
    """Queries MongoDB for a region object

    Args:
        node_id (str): A region_id.

    Returns:
        The single region object retrieved from the database query.
    """
    if not node_id:
        return {'msg': 'invalid cluster_id'}

    # =========================
    # NOTE: REGION GRAPHS
    region_cursor = regions_coll.find({'_id': node_id})
    # TODO: Should be an assertion that region_cursor is of length 1
    region = region_cursor[0]

    # =========================
    # BEGIN SPECIFIC CODE --> Named Entity Graph
    response = {'region_id': region['_id']}
    response['named_entities'] = []
    response['depth'] = region['depth']
    response['size'] = region['size']
    for named_entity in region['named_entities']:
        ne_cursor = named_entities_coll.find({'_id': int(named_entity)})
        for doc in ne_cursor:
            response['named_entities'].append(doc)
    # =========================

    # =========================
    # TODO: GENERIC
    #       This should be the eventual generic code for all region graphs
    # response = {'region_id': region['_id']}
    # response['elements'] = []
    # response['depth'] = region['depth']
    # response['size'] = region['size']
    # for elem_id in region['elements']:
    #     elements_cursor = elements_coll.find({'_id': elem_id})
    #     for elem in elements_cursor:
    #         response['elements'].append(elem)
    # =========================
    # =========================

    # =========================
    # # NOTE: CITESEERX
    # if not node_id:
    #     return {'msg': 'invalid node_id'}
    # if not isinstance(node_id, str):
    #     node_id = str(node_id)

    # cursor = clusters_coll.find({'cluster_id': node_id})
    # dois = [doc['doi'] for doc in cursor]

    # if not dois:
    #     return {'error_message': 'no doi\'s found'}

    # cursor = paper_md_coll.find({'doi': {'$in': dois}})
    # response = {}
    # # NOTE: Remove [0:1] from cursor to show all results
    # for doc in cursor[0:1]:
    #     doc.pop('_id', None)
    #     response[doc['doi']] = doc
    # =========================

    return response


def sink_info(nodes):
    """Gets info for a given set of regions taken as granted to be sinks.

    Args:
        nodes (list): A list of region_id's.

    Returns:
        A dict with region_id as key and a list of elements associated with
        that landmark region as the value.
    """
    # =========================
    # NOTE: REGION GRAPHS
    response = {}
    for node in nodes:
        # FIXME: should this really be node['id'] ?
        region_id = node['label']
        region_cursor = regions_coll.find({'_id': int(region_id)})
        # TODO: Should be an assertion that region_cursor is of length 1
        region = region_cursor[0]

        # =========================
        # BEGIN SPECIFIC CODE --> Named Entity Graph
        named_entities = []
        for ne_id in region['named_entities']:
            named_entities_cursor = \
                named_entities_coll.find({'_id': int(ne_id)})
            for named_entity in named_entities_cursor:
                named_entities.append(named_entity['named_entity'])
        response[region_id] = {}
        response[region_id]['elements'] = ' | '.join(named_entities)
        # the depth is taken to be the last named_entity's number of articles
        response[region_id]['depth'] = len(named_entity['articles'])
        # =========================

        # =========================
        # TODO: GENERIC
        #       This should be the eventual generic code for all region graphs
        # elements = []
        # for elem_id in region['elements']:
        #     elements_cursor = elements_coll.find({'_id': elem_id})
        #     for elem in elements_cursor:
        #         elements.append(elem['content'])
        # response[region_id] = {}
        # response[region_id]['elements'] = \
        #   ' | '.join([str(e) for e in elements])
        # response[region_id]['depth'] = int(region['depth'])
        # =========================
    # =========================

    # =========================
    # NOTE: CITESEERX
    # TODO: Implementation needed
    # =========================

    return response
