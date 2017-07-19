import cPickle as pickle
import graph_tool.all as gt
import numpy as np
from HierarchicalPartitioningTree import PartitionTree, PartitionNode
from PartitionMethods import *


class TreeExploration(object):

    def __init__(self, G):
        if isinstance(G, str):
            G = gt.load_graph(G)
        self.G = G
        self.initialized = False

    def _reached_stopping_criteria(self, node):
        if node.num_siblings() == 0:
            if node.parent is None:
                return False
            if node.parent.num_siblings() == 0:
                if node.parent.parent is None:
                    return False
                return node.parent.parent.num_siblings() == 0
        return False

    def _determine_partition_method(self, node):
        short_label = node.label.split('|')[-1].upper()
        if short_label.startswith('CC'):
            operation = biconnected_components
        elif short_label.startswith('BCC'):
            operation = edge_peel
        elif short_label.startswith('EPL') or short_label == 'ROOT':
            operation = connected_components
        else:
            raise ValueError('Unknown Label')
        return operation

    def create_root(self):
        vp = self.G.new_vp('bool', vals=True)
        ep = self.G.new_ep('bool', vals=True)
        v_idx = np.where(vp.a == 1)[0]
        e_idx = np.where(ep.a == 1)[0]
        T = PartitionTree()
        T.root = PartitionNode(vertex_indices=v_idx,
                               edge_indices=e_idx,
                               partition_type='root',
                               label='root',
                               note='Overall graph, minus vertex peel 1')
        self.T = T
        self.initialized = True
        return self.T.root

    def explore_tree(self, root, threshold=256, check_partition=False):
        stack = []
        stack.append(root)
        while len(stack) > 0:
            node = stack.pop()
            s = '{} --> |V|: {}, |E|: {}'.format(node.label,
                                                 node.num_vertices(),
                                                 node.num_edges())
            if not node.is_leaf():
                for child in node.children:
                    stack.append(child)
                continue
            if node.num_vertices() < threshold:
                continue
            if self._reached_stopping_criteria(node):
                print(s)
                print('Rock')
                continue
            operation = self._determine_partition_method(node)
            vlist = node.vertex_indices
            elist = node.edge_indices
            children = operation(self.G,
                                 vertex_indices=vlist,
                                 edge_indices=elist)
            # this shouldn't happen
            if not children:
                continue
            node.children = children
            v_part = set()
            e_part = set()
            for child in node.children:
                child.parent = node
                child.label = child.parent.label + '|' + child.label
                if check_partition:
                    v_part.update(child.vertex_indices)
                    e_part.update(child.edge_indices)
                stack.append(child)
            if check_partition:
                assert len(v_part) == node.num_vertices()
                assert len(e_part) == node.num_edges()
            node.vertex_indices = []
            node.edge_indices = []

    def create_adjacency_list(root):
        vlist, elist = PartitionTree.collect_indices(root)

        vfilt = self.G.new_vp('bool', vals=False)
        vfilt.a[vlist] = True
        self.G.set_vertex_filter(vfilt)

        efilt = self.G.new_ep('bool', vals=False)
        efilt.a[elist] = True
        self.G.set_edge_filter(efilt)

        for v in self.G.vertices():
            neighbors = [u for u in v.out_neighbours()]
            # First column for v; following columns are neighbors.
            # NOTE: Adjacency list is redundant for undirected graphs
            out_str = '{} ' + ('{} ' * len(neighbors))[:-1] + '\n'
            out_str = out_str.format(v, *neighbors)
            print out_str
