import cPickle as pickle
# import copy
import graph_tool.all as gt
import numpy as np
import os
from collections import Counter
from flask import Flask, jsonify, render_template, request
from app import app
from GraphManager import GraphManager
from Helpers import statistics, to_vis_json, induce_subgraph
from pymongo import MongoClient
from HierarchicalPartitioningTree import PartitionTree, PartitionNode
from PartitionMethods import connected_components, biconnected_components, \
                             edge_peel, k_connected_components

GRAPH_FILES_PATH = 'app/data/graphs/'
TREE_FILES_PATH = 'app/data/trees/'
OPERATIONS = {
    'connected_components': connected_components,
    'biconnected_components': biconnected_components,
    'edge_peel': edge_peel,
    'k_connected_components': k_connected_components
}
float_formatter = lambda x: '{:.2f}'.format(x)
# client = MongoClient('localhost', 27017)
# db = client['citeseerx']
# clusters_coll = db['clusters']
# paper_md_coll = db['paper_metadata']


class Mem:
    T = None
    gm = GraphManager(None)


@app.route('/')
def index():
    # finds all available graph (.gt) files
    graph_files = []
    for file in os.listdir(GRAPH_FILES_PATH):
        if file.endswith('.gt'):
            graph_files.append(file)

    # finds all available tree (.pkl) files
    tree_files = []
    for file in os.listdir(TREE_FILES_PATH):
        if file.endswith('.pkl'):
            tree_files.append(file)

    return render_template('index.html',
                           graph_files=graph_files,
                           tree_files=tree_files)


@app.route('/load-graph')
def load_graph():
    # global Mem.gm
    Mem.gm = GraphManager(None)
    filename = GRAPH_FILES_PATH + request.args.get('filename')
    G = Mem.gm.create_graph(graph_file=filename)
    return render_template('overallGraphStats.html',
                           **statistics(G))


@app.route('/load-tree')
def load_tree():
    # global T
    filename = TREE_FILES_PATH + request.args.get('filename')
    with open(filename, 'rb') as f:
        Mem.T = pickle.load(f)

    return jsonify({'msg': 'tree successfully loaded'})


@app.route('/save-tree')
def save_tree():
    filename = request.args.get('filename')
    if not filename.endswith('.pkl'):
        filename += '.pkl'
    try:
        with open(filename, 'wb') as f:
            pickle.dump(Mem.T, f)
    except Exception as e:
        return jsonify({'msg': str(e)})

    return jsonify({'msg': 'file successfully written'})


@app.route('/get-hnode-children')
def node_children():
    # global T
    if Mem.T is None:
        return 'No hierarchy tree loaded'
    fully_qualified_label = request.args.get('fullyQualifiedLabel')

    node_info = []
    if fully_qualified_label.lower() == 'root':
        for child in Mem.T.root.children:
            # V = len(child.vertex_indices)
            # E = len(child.edge_indices)
            V = child.num_vertices()
            E = child.num_edges()
            short_label = child.label.split('|')[-1]
            node_info.append({
                'fully_qualified_label': child.label,
                'short_label': short_label,
                'num_vertices': V,
                'num_edges': E,
                'vlogv': float_formatter(V * np.log2(V))
            })
        return render_template('treeNodes.html', node_info=node_info)

    # traverse tree
    sub_ids = fully_qualified_label.split('|')
    if sub_ids[0].lower() == 'root':
        sub_ids = sub_ids[1:]
    node = Mem.T.root
    for s in xrange(len(sub_ids)):
        idx = int(sub_ids[s].split('_')[-1])
        node = node.children[idx]

    for child in node.children:
        # V = len(child.vertex_indices)
        # E = len(child.edge_indices)
        V = child.num_vertices()
        E = child.num_edges()
        short_label = child.label.split('|')[-1]
        node_info.append({
            'fully_qualified_label': child.label,
            'short_label': short_label,
            'num_vertices': V,
            'num_edges': E,
            'vlogv': float_formatter(V * np.log2(V))
        })

    return render_template('treeNodes.html', node_info=node_info)


@app.route('/decompose-by-operation')
def decompose_by_operation():
    # global T
    if Mem.T is None:
        return jsonify({'msg': 'No hierarchy tree loaded'})
    if Mem.gm.g is None:
        return jsonify({'msg': 'No graph loaded'})

    fully_qualified_label = request.args.get('fullyQualifiedLabel')
    operation = request.args.get('operation')
    if operation not in OPERATIONS:
        return jsonify({'msg': 'Invalid operation'})

    if fully_qualified_label.lower() == 'root':
        node = Mem.T.root
    else:
        # traverse tree
        sub_ids = fully_qualified_label.split('|')
        if sub_ids[0].lower() == 'root':
            sub_ids = sub_ids[1:]
        node = Mem.T.root
        for s in xrange(len(sub_ids)):
            idx = int(sub_ids[s].split('_')[-1])
            node = node.children[idx]

    if not node.is_leaf():
        return jsonify({'msg': 'Must select a leaf node'})

    vlist = node.vertex_indices
    elist = node.edge_indices
    op = OPERATIONS[operation]
    children = op(Mem.gm.g, vertex_indices=vlist, edge_indices=elist)

    if not children:
        msg = 'Could not decompose any further using method: {}'
        return jsonify({'msg': msg.format(operation)})

    # single child has same vlist and elist
    if len(children) == 1:
        child = children[0]
        # if (len(child.vertex_indices) == len(vlist) and
        #         len(child.edge_indices) == len(elist)):
        if (child.num_vertices() == len(vlist) and 
                child.num_edges() == len(elist)):
            msg = 'Could not decompose any further using method: {}'
            return jsonify({'msg': msg.format(operation)})

    node.children = children
    node_info = []
    for idx, child in enumerate(node.children):
        child.parent = node
        child.label = child.parent.label + '|' + child.label
        # V = len(child.vertex_indices)
        # E = len(child.edge_indices)
        V = child.num_vertices()
        E = child.num_edges()
        short_label = child.label.split('|')[-1]
        node_info.append({
            'fully_qualified_label': child.label + '_' + str(idx),
            'short_label': short_label,
            'num_vertices': V,
            'num_edges': E,
            'vlogv': float_formatter(V * np.log2(V))
        })

    return render_template('treeNodes.html', node_info=node_info)


@app.route('/induce-hnode-subgraph')
def induce_node_subgraph():
    # global T
    if Mem.T is None:
        return jsonify({'msg': 'No hierarchy tree loaded'})
    if Mem.gm.g is None:
        return jsonify({'msg': 'No graph loaded'})

    fully_qualified_label = request.args.get('fullyQualifiedLabel')
    if fully_qualified_label.lower() == 'root':
        vlist = Mem.T.root.vertex_indices
        elist = Mem.T.root.edge_indices
    else:
        # traverse tree
        sub_ids = fully_qualified_label.split('|')
        if sub_ids[0].lower() == 'root':
            sub_ids = sub_ids[1:]
        node = Mem.T.root
        for s in xrange(len(sub_ids)):
            idx = int(sub_ids[s].split('_')[-1])
            node = node.children[idx]
        if node.vertex_indices and node.edge_indices:
            vlist = node.vertex_indices
            elist = node.edge_indices
        else:
            vlist, elist = PartitionTree.collect_indices(node)

    if len(vlist) > 1024:
        return jsonify({'msg': 'Graph is too large to visualize'})

    response = induce_subgraph(Mem.gm.g, vlist, elist)
    return jsonify(response)
