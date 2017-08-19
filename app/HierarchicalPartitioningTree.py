import cPickle as pickle
import graph_tool.all as gt
import numpy as np
import Queue


class PartitionTree(object):

    def __init__(self):
        self.root = None

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

    @classmethod
    def collect_indices(cls, root):
        Q = Queue.Queue()
        vlist = set()
        elist = set()
        Q.put(root)
        while Q.qsize() > 0:
            node = Q.get()
            # TODO (deprecate):
            #   In newly created trees, nodes will always have the cross_edge
            #   attribute, even if it empty, []. Then, the getattr() call can
            #   be replaced with direct call as such: node.cross_edges
            cross_edges = getattr(node, 'cross_edges', [])
            if cross_edges:
                cross_edges = \
                    [e for edges in cross_edges.values() for e in edges]
            elist.update(cross_edges)
            if node.is_leaf():
                vlist.update(node.vertex_indices)
                elist.update(node.edge_indices)
            for child in node.children:
                Q.put(child)
        assert len(vlist) == root.num_vertices()
        assert len(elist) == root.num_edges()
        return list(vlist), list(elist)

    @classmethod
    def traverse_dfs(cls, root, return_stats=False):
        float_formatter = lambda x: '{:.2f}'.format(x)
        stack = []
        stack.append(root)
        nodes = []

        while len(stack) > 0:
            node = stack.pop()
            V = node.num_vertices()
            E = node.num_edges()
            vlogv = float_formatter(V * np.log2(V))
            if node.is_leaf():
                node_type = 'leaf'
                if PartitionNode.is_rock(node,
                                         num_vertices_threshold=512,
                                         check_if_dense=False):
                    node_type += ',rock'
            else:
                node_type = 'intermediate'

            if return_stats:
                nodes.append({
                    'label': node.label,
                    'num_vertices': V,
                    'num_edges': E,
                    'vlogv': vlogv,
                    'node_type': node_type,
                })
            else:
                s = '{}, |V|: {}, |E|: {}, |V|log|V|: {}'
                nodes.append(s.format(node.label, V, E, vlogv))
            for child in node.children[::-1]:
                stack.append(child)
        return nodes


class PartitionNode(object):

    def __init__(self, vertex_indices, edge_indices, label,
                 parent=None, partition_type='vertex', note=''):
        self.vertex_indices = vertex_indices
        self.edge_indices = edge_indices
        self._num_vertices = len(vertex_indices)
        self._num_edges = len(edge_indices)
        if parent is not None:
            if not isinstance(parent, PartitionNode):
                err_msg = 'Parent must be either PartitionNode object or None'
                raise ValueError(err_msg)
        self.label = label
        self.parent = parent
        self.children = []
        self.cross_edges = []
        partition_type = partition_type.lower()
        if partition_type not in ['vertex', 'edge', 'root']:
            err_msg = 'Partition type must be either \'{}\', \'{}\', or \'{}\''
            raise ValueError(err_msg.format('vertex', 'edge', 'root'))
        if partition_type == 'root':
            assert self.parent is None
        self.partition_type = partition_type
        self.note = note

    def __len__(self):
        # if self.partition_type == 'edge':
        #     return len(self.edge_indices)
        # return len(self.vertex_indices)
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

    def num_vertices(self):
        return self._num_vertices

    def num_edges(self):
        return self._num_edges

    def num_children(self):
        return len(self.children)

    def num_siblings(self):
        if self.parent is None:
            return 0
        return len(self.parent.children) - 1

    def remove_children(self):
        if len(self.children) == 0:
            return
        assert self.vertex_indices == []
        assert self.edge_indices == []
        vlist, elist = PartitionTree.collect_indices(self)
        self.vertex_indices = vlist
        self.edge_indices = elist
        assert len(self.vertex_indices) == self.num_vertices()
        assert len(self.edge_indices) == self.num_edges()
        self.cross_edges = []
        self.children = []

    def induce_subgraph(self, G):
        if self.partition_type == 'root':
            print('Node is root. Nothing to induce. G unmodified.')
            return
        G.clear_filters()
        vp = G.new_vp('bool', vals=False)
        ep = G.new_ep('bool', vals=False)

        if self.vertex_indices and self.edge_indices:
            vlist = self.vertex_indices
            elist = self.edge_indices
        else:
            vlist, elist = PartitionTree.collect_indices(self)

        try:
            vp.a[vlist] = True
            ep.a[elist] = True
        except:
            err_msg = 'vertex or edge indices not in G'
            raise IndexError(err_msg)
        G.set_vertex_filter(vp)
        G.set_edge_filter(ep)
        print('Vertex and edge filters applied to G')

    @classmethod
    def is_rock(cls, node, num_vertices_threshold=None, check_if_dense=False):
        if num_vertices_threshold:
            if node.num_vertices() < num_vertices_threshold:
                return False
        if check_if_dense:
            V = node.num_vertices()
            if node.num_edges() < V * np.log2(V):
                return False
        if node.num_siblings() == 0:
            if node.parent is None:
                return False
            if node.parent.num_siblings() == 0:
                if node.parent.parent is None:
                    return False
                return node.parent.parent.num_siblings() == 0
        return False
