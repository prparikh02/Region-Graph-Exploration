import graph_tool.all as gt
import numpy as np
from collections import Counter
from subprocess import Popen, PIPE
from Queue import Queue
from Helpers import *
from HierarchicalPartitioningTree import PartitionTree, PartitionNode
from PartitionMethods import *

OPERATIONS = {
    'connected_components': connected_components,
    'biconnected_components': biconnected_components,
    'edge_peel': edge_peel,
    'peel_one': peel_one,
    'k_connected_components': k_connected_components
}
float_formatter = lambda x: '{:.2f}'.format(x)


def get_node_children(T, fully_qualified_label):
    node = traverse_tree(T, fully_qualified_label)
    node_info = []
    for child in node.children:
        V = child.num_vertices()
        E = child.num_edges()
        short_label = child.label.split('|')[-1]
        node_info.append({
            'fully_qualified_label': child.label,
            'short_label': short_label,
            'num_vertices': V,
            'num_edges': E,
            'vlogv': float_formatter(V * np.log2(V)),
            'is_leaf': child.is_leaf(),
        })

    return {'node_info': node_info}


def remove_node_children(T, fully_qualified_label):
    node = traverse_tree(T, fully_qualified_label)
    node.remove_children()
    return {'node': node}


def induce_subgraph(G, vlist, elist):
    if not G:
        return 'No graph loaded'

    # get proper indices
    vp = G.new_vp('bool', vals=False)
    ep = G.new_ep('bool', vals=False)
    if vlist is []:
        vlist = np.ones_like(vp.a)
    if elist is []:
        elist = np.ones_like(ep.a)
    vp.a[vlist] = True
    ep.a[elist] = True
    G.set_vertex_filter(vp)
    G.set_edge_filter(ep)

    return {'vis_data': to_vis_json(G)}


def decompose_node(T, G, fully_qualified_label, operation):
    if operation not in OPERATIONS:
        return {'msg': 'Invalid operation'}

    node = traverse_tree(T, fully_qualified_label)
    if not node.is_leaf():
        return {'msg': 'Must select a leaf node'}

    vlist = node.vertex_indices
    elist = node.edge_indices
    op = OPERATIONS[operation]
    children = op(G, vertex_indices=vlist, edge_indices=elist)

    if not children:
        msg = 'Could not decompose any further using method: {}'
        return jsonify({'msg': msg.format(operation)})

    # single child has same vlist and elist
    if len(children) == 1:
        child = children[0]
        if (child.num_vertices() == len(vlist) and
                child.num_edges() == len(elist)):
            msg = 'Could not decompose any further using method: {}'
            return {'msg': msg.format(operation)}

    node.children = children
    node_info = []
    for idx, child in enumerate(node.children):
        child.parent = node
        child.label = child.parent.label + '|' + child.label
        V = child.num_vertices()
        E = child.num_edges()
        short_label = child.label.split('|')[-1]
        node_info.append({
            'fully_qualified_label': child.label + '_' + str(idx),
            'short_label': short_label,
            'num_vertices': V,
            'num_edges': E,
            'vlogv': float_formatter(V * np.log2(V)),
            'is_leaf': child.is_leaf(),
        })
    node.vertex_indices = []
    node.edge_indices = []

    return {'node_info': node_info}


def landmark_clustering(G, vlist, elist, cmd):
    vfilt = G.new_vp('bool', vals=False)
    vfilt.a[vlist] = True
    G.set_vertex_filter(vfilt)
    efilt = G.new_ep('bool', vals=False)
    efilt.a[elist] = True
    G.set_edge_filter(efilt)

    p = Popen([cmd], shell=True, stdout=PIPE, stdin=PIPE)

    for v in G.vertices():
        neighbors = [u for u in v.out_neighbours()]
        # First column for v; following columns are neighbors.
        # NOTE: Adjacency list is redundant for undirected graphs
        out_str = ('{} ' +
                   ('{} ' * len(neighbors))[:-1] +
                   '\n').format(v, *neighbors)
        # yield out_str
        p.stdin.write(out_str)
        p.stdin.flush()
    p.stdin.close()

    # get landmarks and clusters
    landmark_map = {}
    cluster_assignment = {}
    while True:
        line = p.stdout.readline()
        if line.strip() == '---':
            break
        v_idx, prev, nearest_landmark = [int(i) for i in line.strip().split()]
        if nearest_landmark == -1:
            landmark_map[v_idx] = len(landmark_map)
            cluster_assignment[v_idx] = v_idx
        else:
            cluster_assignment[v_idx] = nearest_landmark
    cluster_assignment = \
        {k: landmark_map[v] for k, v in cluster_assignment.iteritems()}

    # get spine
    tree = []
    while True:
        line = p.stdout.readline()
        if line == '':
            break
        v_idxs = line.strip().split()
        # if int(v_idxs[-1]) not in landmark_map:
        #     continue
        branch = []
        for i in xrange(len(v_idxs) - 1):
            branch.append(G.edge(v_idxs[i], v_idxs[i + 1]))
        tree.append(branch)

    spine = set(tree[0])
    spine_nodes = set()
    for e in spine:
        spine_nodes.add(e.source())
        spine_nodes.add(e.target())

    branches = set()
    for branch in tree[1:]:
        branches.update(branch)

    vis_data = to_vis_json_cluster_map(G,
                                       cluster_assignment,
                                       landmark_map,
                                       spine,
                                       branches)
    return {
        'vis_data': vis_data
    }


def bcc_tree(G, vlist, elist):
    # get proper indices
    vp = G.new_vp('bool', vals=False)
    ep = G.new_ep('bool', vals=False)
    if vlist is [] or vlist is None:
        vlist = np.ones_like(vp.a)
    if elist is [] or elist is None:
        elist = np.ones_like(ep.a)
    vp.a[vlist] = True
    ep.a[elist] = True
    G.set_vertex_filter(vp)
    G.set_edge_filter(ep)

    # label biconnected components
    bcc, art, _ = gt.label_biconnected_components(G)

    # create metagraph
    Gp = gt.Graph(directed=False)
    Gp.vp['count'] = Gp.new_vp('int', vals=-1)
    Gp.vp['is_articulation'] = Gp.new_vp('bool', vals=False)
    Gp.vp['id'] = Gp.new_vp('string', vals='')
    Gp.ep['count'] = Gp.new_ep('int', vals=0)

    # add bcc metanodes
    # each bcc metanode will be indexed in Gp in increasing order of bcc id,
    #     a scheme which is leveraged later below.
    B = sorted(Counter(bcc.a[elist]).items())
    for b, count in B:
        v = Gp.add_vertex()
        Gp.vp['count'][v] = count

    # add articulation points and metagraph edges
    elist_set = set(elist)
    ap_list = [G.vertex(v) for v in np.where(art.a == 1)[0]]
    for ap in ap_list:
        v = Gp.add_vertex()
        Gp.vp['count'][v] = 1
        Gp.vp['is_articulation'][v] = True
        # assign original vertex_index as art point's id
        Gp.vp['id'][v] = str(G.vertex_index[ap])
        for e in ap.out_edges():
            # NOTE: Following if should never evaluate true...
            if G.edge_index[e] not in elist_set:
                continue
            # add metagraph edge if not already present
            meta_e = Gp.edge(v, Gp.vertex(bcc[e]))
            if not meta_e:
                meta_e = Gp.add_edge(v, Gp.vertex(bcc[e]))
            Gp.ep['count'][meta_e] += 1

    # assert bcc tree is, in fact, a tree
    comp, _ = gt.label_components(G)
    num_components = len(np.unique(comp.a))
    assert Gp.num_edges() == Gp.num_vertices() - num_components

    # TODO: Handle no articulation points (single BCC)
    # articulation point degree distribution
    ap_degrees = [v.out_degree() for v in ap_list]
    ap_deg_bins, ap_deg_counts = \
        zip(*sorted(Counter(ap_degrees).items()))

    # bcc size distribution (no. of edges)
    bcc_size_bins, bcc_size_counts = \
        zip(*sorted(Counter(zip(*B)[-1]).items()))

    vis_data = to_vis_json_bcc_tree(Gp)

    return {
        'vis_data': vis_data,
        'ap_deg_bins': ap_deg_bins,
        'ap_deg_counts': ap_deg_counts,
        'bcc_size_bins': bcc_size_bins,
        'bcc_size_counts': bcc_size_counts,
    }


def bfs_tree(G, vlist, elist, root_idx):
    # set filters
    vfilt = G.new_vp('bool', vals=False)
    vfilt.a[vlist] = True
    G.set_vertex_filter(vfilt)
    efilt = G.new_ep('bool', vals=False)
    efilt.a[elist] = True
    G.set_edge_filter(efilt)

    N = G.num_vertices()
    v = G.vertex(root_idx)
    Q = Queue()
    Q.put(v)
    visited = set()
    visited.add(v)
    tree_edges = []
    while Q.qsize() > 0:
        v = Q.get()
        if len(visited) == N:
            break
        for neighbor in v.out_neighbours():
            if neighbor in visited:
                continue
            visited.add(neighbor)
            Q.put(neighbor)
            tree_edges.append(G.edge(v, neighbor))
    return {G.edge_index[e]: 1 for e in tree_edges}
