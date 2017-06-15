import graph_tool.all as gt
import json
import numpy as np
import pygal
from collections import Counter


def statistics(G):
    if not G:
        return 'No Graph Loaded'
    deg_counts, deg_bins = gt.vertex_hist(G, 'out', float_count=False)
    n = len(deg_counts)
    # vertex_hist = filter(lambda x: x[1] != 0, zip(deg_bins[:-1], deg_counts))
    incl_idx = np.where(deg_counts != 0)[0]
    # vertex_hist = {
    #     'degrees': deg_bins[incl_idx],
    #     'counts': deg_counts[incl_idx]
    # }
    deg_bins = list(deg_bins[incl_idx])
    deg_counts = list(deg_counts[incl_idx])

    comp, cc_hist = gt.label_components(G)
    cc_size_counts = sorted(Counter(cc_hist).items())
    cc_sizes = [csc[0] for csc in cc_size_counts]
    cc_counts = [csc[1] for csc in cc_size_counts]

    num_cc = len(np.unique(comp.a))
    # TODO: number of isolated vertices
    num_singletons = 0
    # if vertex_hist['degrees'][0] == 0:
    #     num_singletons = vertex_hist['counts'][0]
    if deg_bins[0] == 0:
        num_singletons = deg_counts[0]

    return {
        'num_vertices': G.num_vertices(),
        'num_edges': G.num_edges(),
        'num_cc': num_cc,
        'num_singletons': num_singletons,
        'deg_bins': deg_bins,
        'deg_counts': deg_counts,
        'cc_sizes': cc_sizes,
        'cc_counts': cc_counts
        # 'vertex_hist': vertex_hist,
        # 'cc_hist': cc_size_counts
    }


def induce_subgraph(G, vlist, elist):
    if not G:
        return 'No graph loaded'

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

    js_graph = to_vis_json(G, is_bcc_tree=False)

    return {
        'vis_data': {
            'nodes': js_graph['nodes'],
            'edges': js_graph['edges']
        }
    }


def to_vis_json(G, is_bcc_tree=False, filename=None):
    if is_bcc_tree:
        return to_vis_json_bcc_tree(G, filename)

    nodes = []
    for v in G.vertices():
        v_id = G.vp['id'][v]
        label = v_id
        # v_id = G.vertex_index[v]
        # label = G.vp['id'][v]
        is_art = G.vp['is_articulation'][v]
        group = 1 if is_art else 0
        title = label
        value = v.out_degree()
        nodes.append({
            'id': v_id,
            'label': label,
            'title': title,
            'value': value,
            'group': group
        })

    edges = []
    for e in G.edges():
        src = G.vp['id'][e.source()]
        tar = G.vp['id'][e.target()]
        # src = G.vertex_index[e.source()]
        # tar = G.vertex_index[e.target()]
        edges.append({
            'from': src,
            'to': tar
        })

    return {'nodes': nodes, 'edges': edges}


def to_vis_json_bcc_tree(G, filename=None):
    nodes = []
    for v in G.vertices():
        v_id = G.vertex_index[v]
        is_art = G.vp['is_articulation'][v]
        label = v_id
        if is_art:
            count = 1
            title = 'AP: {}'.format(G.vp['id'][v])
            group = 0
        else:
            count = G.vp['count'][v]
            title = 'BCC: {} | Count: {}'.format(v_id, count)
            group = 1
        value = count
        nodes.append({
                'id': v_id,
                'label': label,
                'title': title,
                'value': value,
                'group': group
        })

    edges = []
    for e in G.edges():
        src = G.vertex_index[e.source()]
        tar = G.vertex_index[e.target()]
        edges.append({
                'from': src,
                'to': tar,
            })

    return {'nodes': nodes, 'edges': edges}
