import cPickle as pickle
import graph_tool.all as gt
import numpy as np
from HierarchicalPartitioningTree import PartitionTree, PartitionNode
from PartitionMethods import *
"""TreeExploration

This module provides a helper class that aides in recursively decomposing an
input graph by cycling through the partitioning methods availabe in the
PartitionMethods module. Recursive decomposition ends when a node, its parent,
and its grandparent contain the same exact vertex and edge indices.
"""


class TreeExploration(object):

    def __init__(self, G):
        if isinstance(G, str):
            G = gt.load_graph(G)
        G.clear_filters()
        self.G = G
        self.initialized = False

    def _reached_stopping_criteria(self, node, threshold):
        if node.num_vertices() < threshold:
            return True
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
        elif (short_label.startswith('EPL') or
              short_label.startswith('VP') or
              short_label == 'ROOT'):
            operation = connected_components
        else:
            raise ValueError('Unknown Label')
        return operation

    def _partition_peel_one(self, node):
        vlist = node.vertex_indices
        elist = node.edge_indices
        children = peel_one(self.G)
        self._attach_children(node, children, False)
        if len(children) == 1:
            new_root = children[0] if 'LTE1' not in children[0] else None
        else:
            new_root = \
                children[0] if 'GT1' in children[0].label else children[1]
        return new_root

    def _attach_children(self, node, children, check_partition):
        '''
        Attaches children to node as node.children. Modifies each child with
            new label. Appends each new child to stack.
        NOTE: No return value; input objects are modified instead.
        '''
        node.children = children
        v_part = set()
        e_part = set()
        for child in node.children:
            child.parent = node
            child.label = child.parent.label + '|' + child.label
            if check_partition:
                v_part.update(child.vertex_indices)
                e_part.update(child.edge_indices)
        if check_partition:
            assert len(v_part) == node.num_vertices()
            assert len(e_part) == node.num_edges()
        node.vertex_indices = []
        node.edge_indices = []

    def create_root(self, root_note=''):
        vp = self.G.new_vp('bool', vals=True)
        ep = self.G.new_ep('bool', vals=True)
        v_idx = np.where(vp.a == 1)[0]
        e_idx = np.where(ep.a == 1)[0]
        T = PartitionTree()
        T.root = PartitionNode(vertex_indices=v_idx,
                               edge_indices=e_idx,
                               partition_type='root',
                               label='root',
                               note=root_note)
        self.T = T
        self.initialized = True
        return self.T.root

    def explore_tree(self, root=None, threshold=256,
                     separate_peel_one=True, check_partition=False):
        """
        Begin partitioning by recursively breaking nodes where |V| < threshold.
        'separate_peel_one' creates two children of root node partitioning
            vertices by less than or equal to peel 1 and greater than peel 1
        'check_partition' checks the integrity of the partitioning;
            considerably increases running time
        """

        if not root:
            root = self.T.root

        if separate_peel_one:
            node = self._partition_peel_one(root)
            if node is not None:
                root = node

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
            if self._reached_stopping_criteria(node, threshold):
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
            # modifies node.children; no return
            self._attach_children(node, children, check_partition)
            stack += node.children

    def save_tree(self, filename):
        if not filename.endswith('.pkl'):
            filename += '.pkl'
        with open(filename, 'wb') as f:
            pickle.dump(self.T, f)

    def display_adjacency_list(self, root):
        vlist, elist = PartitionTree.collect_indices(root)

        vfilt = self.G.new_vp('bool', vals=False)
        vfilt.a[vlist] = True
        self.G.set_vertex_filter(vfilt)

        efilt = self.G.new_ep('bool', vals=False)
        efilt.a[elist] = True
        self.G.set_edge_filter(efilt)

        # First column for v; following columns are neighbors.
        # NOTE: Adjacency list is redundant for undirected graphs
        for v in self.G.vertices():
            neighbors = [u for u in v.out_neighbours()]
            out_str = '{} ' + ('{} ' * len(neighbors))[:-1] + '\n'
            out_str = out_str.format(v, *neighbors)
            print out_str
