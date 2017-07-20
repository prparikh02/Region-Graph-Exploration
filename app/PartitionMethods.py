import graph_tool.all as gt
import networkx as nx
import numpy as np
from subprocess import Popen, PIPE
from HierarchicalPartitioningTree import PartitionTree, PartitionNode
from networkx.algorithms.flow import edmonds_karp, shortest_augmenting_path


def connected_components(G, vertex_indices=None, edge_indices=None):
    '''
    Partition Type: Vertex

    Description: Given graph G and sets of both vertex and edge indices,
        induce subgraph and partition vertices by connected components.
    '''

    if not isinstance(G, gt.Graph):
        err_msg = 'G must be a graph_tool.Graph instance'
        raise ValueError(err_msg)

    if vertex_indices is None and edge_indices is None:
        err_msg = 'Must provide either vertex indices or edge indices'
        raise ValueError(err_msg)

    vp = G.new_vp('bool', vals=False)
    ep = G.new_ep('bool', vals=False)
    try:
        vp.a[vertex_indices] = True
        ep.a[edge_indices] = True
    except:
        err_msg = 'vertex or edge indices not in G'
        raise IndexError(err_msg)
    G.set_vertex_filter(vp)
    G.set_edge_filter(ep)

    # label connected components
    comp, _ = gt.label_components(G)

    # avoids having to induce subgraph each time
    # downfall: edge iterator...
    vlists = {}
    elists = {}
    for idx, e in enumerate(G.edges()):
        src = e.source()
        tar = e.target()
        assert comp[src] == comp[tar]
        CC = comp[src]
        if CC not in vlists:
            vlists[CC] = set()
        if CC not in elists:
            elists[CC] = set()
        vlists[CC].add(G.vertex_index[src])
        vlists[CC].add(G.vertex_index[tar])
        elists[CC].add(G.edge_index[e])
        if idx % 500e3 == 0 and idx > 0:
            print idx

    non_isolated_vertices = set()
    children = []
    for idx, CC in enumerate(vlists):
        non_isolated_vertices.update(vlists[CC])
        v_idx = list(vlists[CC])
        e_idx = list(elists[CC])
        node = PartitionNode(vertex_indices=v_idx,
                             edge_indices=e_idx,
                             partition_type='vertex',
                             label='CC_{}_{}'.format(CC, idx),
                             note='Connected Components')
        children.append(node)

    # TODO: Decide whether or not to group all isolated vertices together
    if vertex_indices is not None:
        for idx, v in enumerate(set(vertex_indices) - non_isolated_vertices):
            node = PartitionNode(vertex_indices=[v],
                                 edge_indices=[],
                                 partition_type='vertex',
                                 label='CC_{}_{}'.format(comp[v], idx),
                                 note='Connected Components')
            children.append(node)

    G.clear_filters()
    return children


def biconnected_components(G, vertex_indices=None, edge_indices=None):
    '''
    Partition Type: Edge

    Description: Given graph G and sets of both vertex and edge indices,
        induce subgraph and partition vertices by biconnected components.
    '''

    if not isinstance(G, gt.Graph):
        err_msg = 'G must be a graph_tool.Graph instance'
        raise ValueError(err_msg)

    if vertex_indices is None and edge_indices is None:
        err_msg = 'Must provide either vertex indices or edge indices'
        raise ValueError(err_msg)

    vp = G.new_vp('bool', vals=False)
    ep = G.new_ep('bool', vals=False)
    try:
        vp.a[vertex_indices] = True
        ep.a[edge_indices] = True
    except:
        err_msg = 'vertex or edge indices not in G'
        raise IndexError(err_msg)
    G.set_vertex_filter(vp)
    G.set_edge_filter(ep)

    # label connected components
    bicomp, art, _ = gt.label_biconnected_components(G)

    # avoids having to induce subgraph each time
    # downfall: edge iterator...
    vlists = {}
    elists = {}
    for idx, e in enumerate(G.edges()):
        src = e.source()
        tar = e.target()
        BCC = bicomp[e]
        if BCC not in vlists:
            vlists[BCC] = set()
        if BCC not in elists:
            elists[BCC] = set()
        vlists[BCC].add(G.vertex_index[src])
        vlists[BCC].add(G.vertex_index[tar])
        elists[BCC].add(G.edge_index[e])
        if idx % 500e3 == 0 and idx > 0:
            print idx

    children = []
    print('No. of BCC\'s: {}'.format(len(elists)))
    for idx, BCC in enumerate(elists):
        v_idx = list(vlists[BCC])
        e_idx = list(elists[BCC])
        node = PartitionNode(vertex_indices=v_idx,
                             edge_indices=e_idx,
                             partition_type='edge',
                             label='BCC_{}_{}'.format(BCC, idx),
                             note='Biconnected Components')
        children.append(node)

    # label articulation points
    if 'is_articulation' not in G.vp:
        G.vp['is_articulation'] = G.new_vp('bool', vals=False)
        ap_indices = np.where(art.a == 1)[0]
        G.vp['is_articulation'].a[ap_indices] = True

    G.clear_filters()
    return children


def edge_peel(G, vertex_indices=None, edge_indices=None):
    '''
    Partition Type: Edge

    Description: Given graph G and sets of both vertex and edge indices,
        induce subgraph and partition edges by means of iterative peeling.
    '''

    if not isinstance(G, gt.Graph):
        err_msg = 'G must be a graph_tool.Graph instance'
        raise ValueError(err_msg)

    if vertex_indices is None and edge_indices is None:
        err_msg = 'Must provide either vertex indices or edge indices'
        raise ValueError(err_msg)

    cmd = './app/graph_peeling.bin -t core -o core'

    vp = G.new_vp('bool', vals=False)
    ep = G.new_ep('bool', vals=False)
    try:
        vp.a[vertex_indices] = True
        ep.a[edge_indices] = True
    except:
        err_msg = 'vertex or edge indices not in G'
        raise IndexError(err_msg)
    G.set_vertex_filter(vp)
    G.set_edge_filter(ep)
    efilt = ep

    children = []
    idx = 0
    while G.num_edges() > 0:
        p = Popen([cmd], shell=True, stdout=PIPE, stdin=PIPE)
        for e in G.edges():
            p.stdin.write('{} {}\n'.format(e.source(), e.target()))
            p.stdin.flush()
        p.stdin.close()

        # get line from stdout that contains top peel layer
        top_layer_line = ''
        top_peel = -1
        while True:
            line = p.stdout.readline()
            if line == '':
                break
            if not line.startswith('Core'):
                continue
            peel = int(line.split(' = ')[0].split('_')[-1])
            if not top_layer_line:
                top_layer_line = line
                top_peel = peel
                continue
            if peel > top_peel:
                top_layer_line = line
                top_peel = peel

        # line processing
        label, vertices = top_layer_line.strip().split(' = ')
        peel = int(label.split('_')[-1])
        assert peel == top_peel
        v_idx = [int(v) for v in vertices.split()]

        # keep only relevant vertices/edges and label edge peels
        vfilt = G.new_vp('bool', vals=False)
        vfilt.a[v_idx] = True
        G.set_vertex_filter(vfilt)
        print('peel: {}, |V|: {}, |E|: {}'.format(peel,
                                                  G.num_vertices(),
                                                  G.num_edges()))

        e_idx = np.where(G.new_ep('bool', vals=True).a == 1)[0]
        efilt.a[e_idx] = False
        node = PartitionNode(vertex_indices=v_idx,
                             edge_indices=e_idx,
                             partition_type='edge',
                             label='EPL_{}_{}'.format(peel, idx),
                             note='peel {}'.format(peel))
        children.append(node)
        idx += 1
        G.set_vertex_filter(vp)
        G.set_edge_filter(efilt)

    G.clear_filters()
    return children


def peel_one(G, vertex_indices=None, edge_indices=None):
    '''
    Partition Type: Node

    Description: Given graph G and sets of both vertex and edge indices,
        induce subgraph and group nodes as either peel less than or equal to 1,
        or greater than 1.
    '''

    if not isinstance(G, gt.Graph):
        err_msg = 'G must be a graph_tool.Graph instance'
        raise ValueError(err_msg)

    if vertex_indices is None and edge_indices is None:
        err_msg = 'Must provide either vertex indices or edge indices'
        raise ValueError(err_msg)

    cmd = './app/graph_peeling.bin -t core -o core'

    vp = G.new_vp('bool', vals=False)
    ep = G.new_ep('bool', vals=False)
    try:
        vp.a[vertex_indices] = True
        ep.a[edge_indices] = True
    except:
        err_msg = 'vertex or edge indices not in G'
        raise IndexError(err_msg)
    G.set_vertex_filter(vp)
    G.set_edge_filter(ep)
    efilt = ep

    children = []
    v_idx = []
    p = Popen([cmd], shell=True, stdout=PIPE, stdin=PIPE)
    for e in G.edges():
        p.stdin.write('{} {}\n'.format(e.source(), e.target()))
        p.stdin.flush()
    p.stdin.close()

    peel_zero_line = ''
    peel_one_line = ''
    while True:
        line = p.stdout.readline()
        if line == '':
            break
        if not line.startswith('Core'):
            continue
        peel = int(line.split(' = ')[0].split('_')[-1])
        if peel == 0:
            peel_zero_line = line
        elif peel == 1:
            peel_one_line = line

    # line processing
    if peel_zero_line:
        label, vertices = peel_zero_line.strip().split(' = ')
        peel = int(label.split('_')[-1])
        assert peel == 0
        v_idx += [int(v) for v in vertices.split()]
    if peel_one_line:
        label, vertices = peel_one_line.strip().split(' = ')
        peel = int(label.split('_')[-1])
        assert peel == 1
        v_idx += [int(v) for v in vertices.split()]

    if not v_idx:
        # if graph has no nodes of peel value less than or equal to 1
        node = PartitionNode(vertex_indices=vertex_indices,
                             edge_indices=edge_indices,
                             partition_type='vertex',
                             label='VP_GT1_{}'.format(0),
                             note='peel values greater than (GT) 1')
        children.append(node)
        return children
    elif v_idx == vertex_indices:
        # if graph has no nodes of peel value greater than 1
        node = PartitionNode(vertex_indices=vertex_indices,
                             edge_indices=edge_indices,
                             partition_type='vertex',
                             label='VP_LT1_{}'.format(0),
                             note='peel values less than or equal to (LTE) 1')
        children.append(node)
        return children

    # graph contains nodes of peel values both less than or equal to 1 and
    #   greater than 1
    # keep only relevant vertices/edges and label edge peels
    vfilt = G.new_vp('bool', vals=False)
    vfilt.a[v_idx] = True
    G.set_vertex_filter(vfilt)
    print('peel: {}, |V|: {}, |E|: {}'.format(1,
                                              G.num_vertices(),
                                              G.num_edges()))

    e_idx = np.where(G.new_ep('bool', vals=True).a == 1)[0]
    efilt.a[e_idx] = False
    node = PartitionNode(vertex_indices=v_idx,
                         edge_indices=e_idx,
                         partition_type='vertex',
                         label='VP_LTE1_{}'.format(0),
                         note='peel values less than or equal to (LTE) 1')
    children.append(node)

    # get indices for peel values greater than 1
    v_idx = list(set(vertex_indices) - set(v_idx))
    e_idx = list(set(edge_indices) - set(e_idx))
    node = PartitionNode(vertex_indices=v_idx,
                         edge_indices=e_idx,
                         partition_type='vertex',
                         label='VP_GT1_{}'.format(1),
                         note='peel values greater than (GT) 1')
    children.append(node)

    G.clear_filters()
    return children


def k_connected_components(G, vertex_indices=None, edge_indices=None):
    '''
    Partition Type: TBD (kind of vertex and edge, but not really a partition)

    Description: Given graph G and sets of both vertex and edge indices,
        induce subgraph and maximally break (NOT PARTITION) into k-connected
        components.
    '''

    if not isinstance(G, gt.Graph):
        err_msg = 'G must be a graph_tool.Graph instance'
        raise ValueError(err_msg)

    if vertex_indices is None and edge_indices is None:
        err_msg = 'Must provide either vertex indices or edge indices'
        raise ValueError(err_msg)

    vp = G.new_vp('bool', vals=False)
    ep = G.new_ep('bool', vals=False)
    try:
        vp.a[vertex_indices] = True
        ep.a[edge_indices] = True
    except:
        err_msg = 'vertex or edge indices not in G'
        raise IndexError(err_msg)
    G.set_vertex_filter(vp)
    G.set_edge_filter(ep)

    H = nx.Graph()
    for e in G.edges():
        src_idx = G.vertex_index[e.source()]
        tar_idx = G.vertex_index[e.target()]
        H.add_edge(src_idx, tar_idx)

    if G.num_edges() > G.num_vertices() * np.log2(G.num_vertices()):
        flow_func = shortest_augmenting_path
    else:
        flow_func = edmonds_karp
    k_components = nx.k_components(H, flow_func=flow_func)
    for k, vertex_sets in k_components.iteritems():
        print('k = {} | No. of Components: {}'.format(k, len(vertex_sets)))
        for vs in vertex_sets:
            print('    {}'.format(vs))
        print('')

    # make meta graph
    largest_k = max(k_components.keys())

    N = len(k_components[largest_k])
    for s in k_components[largest_k]:
        pass
