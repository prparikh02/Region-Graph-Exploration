import graph_tool.all as gt
import json
import numpy as np
from collections import Counter
from subprocess import Popen, PIPE


def kcore_decomposition(G, vlist=[], elist=[]):
    '''
    Synonymous with graph vertex peeling.
    Returns dict with keys as kcore values and
        values as vertex IDs.
    '''
    # initiate filters, if necessary
    if vlist or elist:
        vp = G.new_vp('bool', vals=False)
        ep = G.new_ep('bool', vals=False)
        if vlist is []:
            vlist = np.ones_like(vp.a)
        elif elist is []:
            elist = np.ones_like(ep.a)
        vp.a[vlist] = True
        ep.a[elist] = True
        G.set_vertex_filter(vp)
        G.set_edge_filter(ep)

    cmd = './app/bin/graph_peeling.bin -t core -o core'
    p = Popen([cmd], shell=True, stdout=PIPE, stdin=PIPE)
    for e in G.edges():
        p.stdin.write('{} {}\n'.format(e.source(), e.target()))
        p.stdin.flush()
    p.stdin.close()

    peel_partition = {}
    while True:
        line = p.stdout.readline()
        if line == '':
            break
        if not line.startswith('Core'):
            continue
        peel, vertices = line.split(' = ')
        peel = int(peel.split('_')[-1])
        vertices = vertices.strip().split()
        peel_partition[peel] = vertices

    return peel_partition


def statistics(G):
    if not G:
        return 'No Graph Loaded'
    float_formatter = lambda x: '{:.2f}'.format(x)

    if G.get_vertex_filter()[0] is not None:
        vfilt = G.get_vertex_filter()[0]
        v_idx = np.where(vfilt.a == 1)[0]
    else:
        v_idx = np.arange(G.num_vertices())

    deg_counts, deg_bins = gt.vertex_hist(G, 'out', float_count=False)
    incl_idx = np.where(deg_counts != 0)[0]
    deg_bins = list(deg_bins[incl_idx])
    deg_counts = list(deg_counts[incl_idx])

    comp, cc_hist = gt.label_components(G)
    cc_size_counts = sorted(Counter(cc_hist).items())
    cc_sizes = [csc[0] for csc in cc_size_counts]
    cc_counts = [csc[1] for csc in cc_size_counts]

    num_cc = len(np.unique(comp.a))
    if deg_bins[0] == 0:
        num_singletons = deg_counts[0]
    else:
        num_singletons = 0

    if G.get_vertex_filter()[0] and G.get_edge_filter()[0]:
        # Always correct, but much slower
        peel_partition = kcore_decomposition(G)
        peel_bins = sorted(peel_partition.keys())
        peel_counts = [len(peel_partition[k]) for k in peel_bins]
    else:
        # Very fast, but unstable (not always accurate) for graphs with filters
        kcore = gt.kcore_decomposition(G)
        C = Counter(kcore.a[v_idx])
        peel_bins, peel_counts = [list(t) for t in zip(*C.items())]

    vlogv = G.num_vertices() * np.log2(G.num_vertices())

    return {
        'num_vertices': G.num_vertices(),
        'num_edges': G.num_edges(),
        'num_cc': num_cc,
        'num_singletons': num_singletons,
        'vlogv': float_formatter(vlogv),
        'deg_bins': deg_bins,
        'deg_counts': deg_counts,
        'cc_sizes': cc_sizes,
        'cc_counts': cc_counts,
        'peel_bins': peel_bins,
        'peel_counts': peel_counts,
    }


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


def bcc_tree(G, vlist, elist):
    # get proper indices
    vp = G.new_vp('bool', vals=False)
    ep = G.new_ep('bool', vals=False)
    if vlist is [] or not vlist:
        vlist = np.ones_like(vp.a)
    if elist is [] or not elist:
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


def landmark_clustering(G, vlist, elist, cmd=None):
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


def to_vis_json(G, filename=None):
    nodes = []
    for v in G.vertices():
        # v_id = G.vp['id'][v]
        # label = v_id
        v_id = G.vertex_index[v]
        label = G.vp['id'][v]
        group = 1
        title = label
        value = v.out_degree()
        nodes.append({
            'id': v_id,
            'label': label,
            'title': title,
            'value': value,
            'group': group,
        })

    edges = []
    for e in G.edges():
        # src = G.vp['id'][e.source()]
        # tar = G.vp['id'][e.target()]
        src = G.vertex_index[e.source()]
        tar = G.vertex_index[e.target()]
        edges.append({
            'id': G.edge_index[e],
            'from': src,
            'to': tar,
            # 'value': 1,
        })

    return {'nodes': nodes, 'edges': edges}


def to_vis_json_bcc_tree(G, filename=None):
    AP_GROUP = 0
    BCC_METANODE_GROUP = 1
    nodes = []
    for v in G.vertices():
        v_id = G.vertex_index[v]
        count = G.vp['count'][v]
        is_art = G.vp['is_articulation'][v]
        if is_art:
            label = G.vp['id'][v]
            title = 'AP: {}'.format(label)
            group = AP_GROUP
        else:
            title = 'BCC: {} | Count: {}'.format(v_id, count)
            label = title
            group = BCC_METANODE_GROUP
        value = count
        nodes.append({
                'id': v_id,
                'label': label,
                'title': title,
                'value': value,
                'group': group,
        })

    edges = []
    for e in G.edges():
        src = G.vertex_index[e.source()]
        tar = G.vertex_index[e.target()]
        edges.append({
                'id': G.edge_index[e],
                'from': src,
                'to': tar,
                'value': G.ep['count'][e],
            })

    return {'nodes': nodes, 'edges': edges}


def to_vis_json_cluster_map(G,
                            cluster_assignment,
                            landmark_map,
                            spine,
                            branches):
    nodes = []
    for v in G.vertices():
        v_id = G.vertex_index[v]
        label = G.vp['id'][v]
        title = label
        value = v.out_degree()
        group = cluster_assignment[v_id]
        if v_id in landmark_map:
            shape = 'star'
            border_width = 2
        else:
            shape = 'dot'
            border_width = 1
        nodes.append({
            'id': v_id,
            'label': label,
            'title': title,
            'value': value,
            'group': group,
            'shape': shape,
            'borderWidth': border_width,
        })

    edges = []
    for e in G.edges():
        src = G.vertex_index[e.source()]
        tar = G.vertex_index[e.target()]
        if e in spine:
            category = 'spine'
        elif e in branches:
            category = 'branch'
        else:
            category = 'none'
        edges.append({
            'id': G.edge_index[e],
            'from': src,
            'to': tar,
            'category': category,
            # 'value': 1,
        })

    return {'nodes': nodes, 'edges': edges}
