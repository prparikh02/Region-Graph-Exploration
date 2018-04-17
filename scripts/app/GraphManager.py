import graph_tool.all as gt


class GraphManager(object):
    """Utility class for loading a graph-tool graph.

    Loads a graph from either a '.gt' file or from an edge list plaintext file.
    """

    def __init__(self, edges_file):
        self.edges_file = edges_file

    def _read_edges(self):
        delimiter = '\t'
        self.edges = set()
        self.nodes = set()
        with open(self.edges_file) as f:
            for idx, line in enumerate(f):
                src, tar = line.strip().split(delimiter)
                self.edges.add((src, tar))
                self.nodes.add(src)
                self.nodes.add(tar)
                if idx % 1e6 == 0:
                    print('{} edges loaded'.format(idx))
        print('nodes and edges loaded')

    def initialize(self):
        self._read_edges()

    def create_graph(self, graph_file=None, save_file='csx_graph.gt'):
        self.vertex_idx_map = {}
        if graph_file:
            try:
                g = gt.load_graph(graph_file)
                print g.list_properties()
                if 'id' not in g.vp:
                    g.vp['id'] = g.new_vp('int', vals=g.get_vertices())
                for v in g.vertices():
                    self.vertex_idx_map[g.vp['id'][v]] = g.vertex_index[v]
                self.g = g
                print('Loading graph from file: Succeeded')
                return self.g
            except IOError as e:
                print('Loading graph from file: Failed - {}'.format(e))

        g = gt.Graph(directed=False)
        # add vertices
        g.vp['id'] = g.new_vp("string")
        for idx, node in enumerate(self.nodes):
            v = g.add_vertex()
            g.vp['id'][v] = node
            self.vertex_idx_map[node] = v
            if idx % 100e3 == 0:
                print('Adding vertex {}'.format(idx))
        print('Vertices added')

        for idx, edge in enumerate(self.edges):
            src, tar = edge
            e = g.add_edge(self.vertex_idx_map[src],
                           self.vertex_idx_map[tar])
            if idx % 1e6 == 0:
                print('Adding edge {}'.format(idx))
        print('Edges added')

        self.g = g
        self.g.save(save_file)
        print('Graph created and saved')
        return self.g
