import cPickle as pickle
import graph_tool.all as gt
import numpy as np


class PartitionTree(object):

    def __init__(self):
        self.root = None
        self.inverted_index = {}

    # def __repr__(self):
    #     pass

    def __str__(self):
        pass

    def __len__(self):
        pass

    def __iter__(self):
        pass

    def check_integrity(self, G):
        # TODO: Recursively check each node's indices fall within graph G.
        # TODO: Verify length of childrens' indices is less than those of self
        pass

    def save(self, filename):
        if not isinstance(filename, str):
            err_msg = 'filename must be string'
            raise ValueError(err_msg)
        with open(filename, 'wb') as f:
            pickle.dump(self, f)


class PartitionNode(object):

    def __init__(self, vertex_indices, edge_indices, label,
                 parent=None, partition_type='vertex', note=''):
        self.vertex_indices = vertex_indices
        self.edge_indices = edge_indices
        if parent is not None:
            if not isinstance(parent, PartitionNode):
                err_msg = 'Parent must be either PartitionNode object or None'
                raise ValueError(err_msg)
        self.label = label
        self.parent = parent
        self.children = []
        partition_type = partition_type.lower()
        if partition_type not in ['vertex', 'edge', 'root']:
            err_msg = 'Partition type must be either \'{}\', \'{}\', or \'{}\''
            raise ValueError(err_msg.format('vertex', 'edge', 'root'))
        if partition_type == 'root':
            assert self.parent is None
        self.partition_type = partition_type
        self.note = note

    def __len__(self):
        if self.partition_type == 'edge':
            return len(self.edge_indices)
        return len(self.vertex_indices)

    def parent_by_partition_type(self, partition_type=None):
        if not partition_type:
            partition_type = self.partition_type
        curr = self.parent
        while True:
            # No parent of same partition type so return self
            if not curr:
                return self
            if curr.partition_type == partition_type:
                return curr
            curr = curr.parent

    def is_root(self):
        return not self.parent

    def is_leaf(self):
        return len(self.children) == 0

    def induce_subgraph(self, G):
        if self.partition_type == 'root':
            print('Node is root. Nothing to induce. G unmodified.')
            return
        G.clear_filters()
        vp = G.new_vp('bool', vals=False)
        ep = G.new_ep('bool', vals=False)
        try:
            vp.a[self.vertex_indices] = True
            ep.a[self.edge_indices] = True
        except:
            err_msg = 'vertex or edge indices not in G'
            raise IndexError(err_msg)
        G.set_vertex_filter(vp)
        G.set_edge_filter(ep)
        print('Vertex and edge filters applied to G')
