import graph_tool.all as gt
import numpy as np
from subprocess import Popen, PIPE
from HierarchicalPartitioningTree import PartitionTree, PartitionNode


def connected_components(G, vertex_indices=None, edge_indices=None):
    '''
    Partition Type: Vertex

    Description: Given graph G and sets of indices, vertex and/or edge indices,
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
    vp.a[vertex_indices] = True
    ep.a[edge_indices] = True
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

    Description: Given graph G and sets of indices, vertex and/or edge indices,
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
    vp.a[vertex_indices] = True
    ep.a[edge_indices] = True
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

    cmd = './app/graph_peeling.bin -t core -o core'

    vp = G.new_vp('bool', vals=False)
    ep = G.new_ep('bool', vals=False)
    vp.a[vertex_indices] = True
    ep.a[edge_indices] = True
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
                             label='epl_{}_{}'.format(peel, idx),
                             note='peel {}'.format(peel))
        children.append(node)
        idx += 1
        G.set_vertex_filter(vp)
        G.set_edge_filter(efilt)

    G.clear_filters()
    return children
