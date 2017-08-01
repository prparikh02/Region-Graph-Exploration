import cPickle as pickle
import graph_tool.all as gt
import numpy as np
import os
from Queue import Queue
from flask import Flask, jsonify, render_template, request
from app import app
from Database_Handlers import *
from GraphManager import GraphManager
from Handlers import *
from Helpers import *
from HierarchicalPartitioningTree import PartitionTree, PartitionNode
from PartitionMethods import *

GRAPH_FILES_PATH = 'app/data/graphs/'
TREE_FILES_PATH = 'app/data/trees/'
CLUSTER_FILES_PATH = 'app/bin/cluster_methods/'
ADJACENCY_OUT_PATH = 'app/adjacency_out/'


class Mem:
    T = None
    gm = GraphManager(None)
    # TODO: Do we really need this current_view?
    current_view = {}


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

    # find all available cluster method binaries
    clustering_files = []
    for file in os.listdir(CLUSTER_FILES_PATH):
        if file.endswith('.bin'):
            clustering_files.append(file)

    return render_template('index.html',
                           graph_files=graph_files,
                           tree_files=tree_files,
                           clustering_files=clustering_files,)


@app.route('/load-graph')
def load_graph():
    Mem.gm = GraphManager(None)
    filename = GRAPH_FILES_PATH + request.args.get('filename')
    G = Mem.gm.create_graph(graph_file=filename)
    notes = ''
    if 'notes' in G.graph_properties:
        notes = G.graph_properties['notes']
    return render_template('overallGraphStats.html',
                           notes=notes,
                           **statistics(G))


@app.route('/load-tree')
def load_tree():
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
    fully_qualified_label = request.args.get('fullyQualifiedLabel')

    response = get_node_children(Mem.T, fully_qualified_label)
    assert 'node_info' in response

    node_info = response['node_info']
    tree_nodes_html = render_template('treeNodes.html', node_info=node_info)

    return jsonify({
        'tree_nodes_html': tree_nodes_html,
        'node_info': node_info,
    })


@app.route('/remove-hnode-children')
def remove_hnode_children():
    fully_qualified_label = request.args.get('fullyQualifiedLabel')

    response = remove_node_children(Mem.T, fully_qualified_label)
    assert 'node' in response

    return response['node'].label


@app.route('/decompose-by-operation')
def decompose_by_operation():
    fully_qualified_label = request.args.get('fullyQualifiedLabel')
    operation = request.args.get('operation')

    response = \
        decompose_node(Mem.T, Mem.gm.g, fully_qualified_label, operation)
    if 'msg' in response:
        return jsonify(response)
    assert 'node_info' in response

    return render_template('treeNodes.html', **response)


@app.route('/induce-hnode-subgraph')
def induce_node_subgraph():
    fully_qualified_label = request.args.get('fullyQualifiedLabel')
    vlist, elist = get_indices(Mem.T, fully_qualified_label)
    if len(vlist) > 2194:
        return jsonify({'msg': 'Graph is too large to visualize'})

    Mem.current_view['vlist'] = vlist
    Mem.current_view['elist'] = elist

    response = induce_subgraph(Mem.gm.g, vlist, elist)
    return jsonify(response)


@app.route('/cluster-by-landmarks')
def cluster_by_landmarks():
    fully_qualified_label = request.args.get('fullyQualifiedLabel')
    filename = request.args.get('filename')
    cmd = CLUSTER_FILES_PATH + filename

    vlist, elist = get_indices(Mem.T, fully_qualified_label)
    Mem.current_view['vlist'] = vlist
    Mem.current_view['elist'] = elist

    response = landmark_clustering(Mem.gm.g, vlist, elist, cmd)
    return jsonify(response)


@app.route('/landmark-regions')
def get_landmark_regions():
    clusters = json.loads(request.args.get('clusters'))
    response = landmark_regions(clusters)
    return jsonify(response)


@app.route('/get-intracluster-summary')
def get_intracluster_summary():
    nodes = json.loads(request.args.get('nodes'))
    response = intracluster_summary(nodes)
    return jsonify(response)


@app.route('/doc-lookup')
def do_doc_lookup():
    node_id = int(request.args.get('node_id'))
    response = doc_lookup(node_id)
    return jsonify(response)


@app.route('/get-hierarchy-tree')
def get_hierarchy_tree():
    nodes = PartitionTree.traverse_dfs(Mem.T.root, return_stats=True)
    return jsonify({'nodes': nodes})


@app.route('/bfs-tree')
def compute_bfs_tree():
    if not Mem.current_view:
        return jsonify({'msg': 'Current view not set'})

    # rootNodeID returned is actually vertex index in graph
    root_idx = int(request.args.get('rootNodeID'))
    # O(|V|) operation; consider removing
    assert root_idx in Mem.current_view['vlist']
    vlist = Mem.current_view['vlist']
    elist = Mem.current_view['elist']

    response = bfs_tree(Mem.gm.g, vlist, elist, root_idx)
    return jsonify(response)


@app.route('/compute-bcc-tree')
def compute_bcc_tree():
    fully_qualified_label = request.args.get('fullyQualifiedLabel')
    vlist, elist = get_indices(Mem.T, fully_qualified_label)
    return jsonify(bcc_tree(Mem.gm.g, vlist, elist))


@app.route('/save-adjacency-list')
def save_adjacency_list():
    fully_qualified_label = request.args.get('fullyQualifiedLabel')
    vlist, elist = get_indices(Mem.T, fully_qualified_label)

    filename = ADJACENCY_OUT_PATH + fully_qualified_label + '.txt'
    try:
        response = save_adjacency(Mem.gm.g, vlist, elist, filename)
    except Exception as e:
        return jsonify({'msg': str(e)})

    return jsonify(response)
