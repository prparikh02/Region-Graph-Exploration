import cPickle as pickle
import graph_tool.all as gt
import time
from argparse import ArgumentParser, RawTextHelpFormatter


def init_argparser():
    description = ('Given an input file in which each line represents the '
                   'elements (id\'s) of a single set, compute the region '
                   'graph.')
    parser = ArgumentParser(description=description,
                            formatter_class=RawTextHelpFormatter)

    parser.add_argument('input_file', metavar='input', type=str,
                        help='input path of set file')

    parser.add_argument('output_prefix', metavar='output_prefix', type=str,
                        help='prefix (including path) of output files')

    next_highest_depth_descr = \
        '\nLinear in |S|, but ultimately depends on topology\n\n' \
        'Region A will have an directed edge to Region B if:\n' \
        ' - Region A != Region B' \
        ' - Region A and Region B come from the same generating set\n' \
        ' - Region A and Region B have \'consecutive\' depths:\n' \
        '  - Region B has strictly next highest depth w/r/t depth of ' \
        'Region A'
    depth_diff_descr = \
        '\nLinear in |S|, but ultimately depends on topology.\n\n' \
        'Region A will have an directed edge to Region B if:\n' \
        ' - Region A != Region B\n' \
        ' - Region A and Region B come from the same generating set\n' \
        ' - depths of Region A and Region B differ by at most ' \
        '\'max_depth_diff\''
    depth_diff_strict_descr = \
        '\nLet |R| be number of regions\n' \
        'O(|R|^2)\n\n' \
        'Region A will have an directed edge to Region B if:\n' \
        ' - Region A != Region B\n' \
        ' - Region A\'s generating set is a subset of that of Region B\'s\n' \
        ' - depths of Region A and Region B differ by at most ' \
        '\'max_depth_diff\''
    regions_connection_help = \
        ('determines the way in which regions are '
         'connected. Available options:\n\n'
         '\'next-highest-depth\': {}\n\n'
         '\'depth-difference\' (default): {}\n\n'
         '\'depth-difference-strict\': {}').format(next_highest_depth_descr,
                                                   depth_diff_descr,
                                                   depth_diff_strict_descr)
    parser.add_argument('-r', '--regions-connection', type=str, metavar='',
                        dest='connection_type', default='depth-difference',
                        help=regions_connection_help)

    parser.add_argument('-m', '--max-depth-diff', type=int, metavar='',
                        dest='max_depth_diff', default=1,
                        help='the maximum depth difference between two '
                             'regions for them to be eligible to be '
                             'neighbors')

    return parser


def depth_difference_strict(regions, max_depth_diff=1):
    '''
    Create graph of regions.
    Let |R| be number of regions.
    O(|R|^2)

    Region A will have an directed edge to Region B if:
        - Region A != Region B
        - Region A's generating set is a subset of that of Region B's
        - depths of Region A and Region B differ by at most 'max_depth_diff'
    '''
    adjacency = {}
    # this can be optimized if regions is a list where index is id
    #     reduces number of checks to 1/2
    t0 = time.time()
    for idx, r_i in enumerate(regions):
        if idx % 100 == 0 and idx > 0:
            print('{} / {} -- {}'.format(idx,
                                         len(regions),
                                         time.time() - t0))
        depth_i = len(regions[r_i]['sets'])
        generating_sets_i = regions[r_i]['sets']
        for r_j in regions:
            if r_j not in adjacency:
                adjacency[r_j] = set()
            if r_i == r_j:
                continue
            depth_j = len(regions[r_j]['sets'])
            if abs(depth_i - depth_j) > max_depth_diff:
                continue
            generating_sets_j = regions[r_j]['sets']
            # small control check to avoid multiple issubset calls
            if depth_i <= depth_j:
                if generating_sets_i.issubset(generating_sets_j):
                    adjacency[r_i].add(r_j)
            else:
                if generating_sets_j.issubset(generating_sets_i):
                    adjacency[r_j].add(r_i)

    return adjacency


def depth_difference(regions, set_region_composition, max_depth_diff=1):
    '''
    Create graph of regions.
    Linear in |S|, but ultimately depends on topology.

    Region A will have an directed edge to Region B if:
        - Region A != Region B
        - Region A and Region B come from the same generating set
        - depths of Region A and Region B differ by at most 'max_depth_diff'
    '''
    adjacency = {}
    # loop through each set and the regions composing it
    for idx, (s_id, composing_regions) in \
            enumerate(set_region_composition.iteritems()):
        for r_i in composing_regions:
            generating_sets_i = regions[r_i]['sets']
            depth_i = len(generating_sets_i)
            for r_j in composing_regions:
                # insert region into adjacency if seen for first time
                if r_j not in adjacency:
                    adjacency[r_j] = set()
                # continue if comparing same regions
                if r_i == r_j:
                    continue
                # check if pair has already been considered
                if r_i in adjacency[r_j] or r_j in adjacency[r_i]:
                    continue
                generating_sets_j = regions[r_j]['sets']
                depth_j = len(generating_sets_j)
                # do not connect regions if their depths differ too much
                if abs(depth_i - depth_j) > max_depth_diff:
                    continue
                # connect from greater depth to lesser depth
                # TODO: how to handle equal to?
                # TODO: should we check if generating sets are subsets?
                if depth_i > depth_j:
                    adjacency[r_i].add(r_j)
                    # if generating_sets_j.issubset(generating_sets_i):
                    #     adjacency[r_i].add(r_j)
                elif depth_i < depth_j:
                    adjacency[r_j].add(r_i)
                    # if generating_sets_i.issubset(generating_sets_j):
                    #     adjacency[r_j].add(r_i)
                else:
                    # included for explicitness
                    pass

    return adjacency


def next_highest_depth(regions, set_region_composition):
    '''
    Create graph of regions.
    Linear in |S|, but ultimately depends on topology.

    Region A will have an directed edge to Region B if:
        - Region A != Region B
        - Region A and Region B come from the same generating set
        - Region A and Region B have 'consecutive' depths
            - Region B has strictly next highest depth w/r/t depth of Region A
    '''
    adjacency = {}
    # loop through each set and the regions composing it
    for idx, (s_id, composing_regions) in \
            enumerate(set_region_composition.iteritems()):
        depths = [len(regions[r]['sets']) for r in composing_regions]
        depths = sorted(list(set(depths)))
        # TODO: if all regions have single depth
        depth_map = dict(zip(depths[:-1], depths[1:]))
        max_depth = max(depths)
        if len(depths) == 1:
            print depths
        for r_i in composing_regions:
            generating_sets_i = regions[r_i]['sets']
            depth_i = len(generating_sets_i)
            if depth_i == max_depth:
                continue
            for r_j in composing_regions:
                # insert region into adjacency if seen for first time
                if r_j not in adjacency:
                    adjacency[r_j] = set()
                # continue if comparing same regions
                if r_i == r_j:
                    continue
                # check if pair has already been considered
                if r_i in adjacency[r_j] or r_j in adjacency[r_i]:
                    continue
                generating_sets_j = regions[r_j]['sets']
                depth_j = len(generating_sets_j)
                if depth_j == max_depth:
                    continue
                # connect from lesser depth to greater depth
                if depth_map[depth_i] == depth_j:
                    adjacency[r_i].add(r_j)
                elif depth_map[depth_j] == depth_i:
                    adjacency[r_j].add(r_i)

    return adjacency


def read_sets(filename):
    '''
    Reading input
    O(sum of cardinalities of input sets)

    'S' -
        key: set id
        value: member elements
    'elem_assoc' -
          key: element
          value: sets to which element belongs

    returns 'S', 'elem_assoc'

    If input set file already has ids provided (set_id >> elem0, elem1, ...),
    they will be used. Otherwise, each line will be labeled 0 to (# of lines).
    '''
    DELIMITER = ' >> '
    S = {}
    elem_assoc = {}
    with open(filename, 'r') as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            split_line = line.strip().split(DELIMITER)
            print split_line
            if len(split_line) == 1:
                set_id = idx
                elems = split_line[0].split()
            elif len(split_line) == 2:
                set_id = split_line[0]
                elems = split_line[1].split()
            else:
                print('May need to change DELIMITER...')
            S[set_id] = set(elems)
            for elem in elems:
                if elem not in elem_assoc:
                    elem_assoc[elem] = set()
                elem_assoc[elem].add(set_id)
    elem_assoc.update((k, frozenset(v)) for k, v in elem_assoc.iteritems())

    return S, elem_assoc


def find_regions(elem_assoc):
    '''
    Finding regions and some bookkeeping
    O(number of unique elements) or O(size of universe)

    'inv_idx' -
        key: regions (frozensets, immutable and therefore hashable)
        value: elements of thsoe regions

    'regions' -
        key: unique region id
        value: map such that -
            key: sets that generate the region
            value: elements of the region

    returns 'regions'
    '''
    inv_idx = {}
    for k, v in elem_assoc.iteritems():
        if v not in inv_idx:
            inv_idx[v] = []
        inv_idx[v].append(k)

    regions = {}
    for idx, (k, v) in enumerate(inv_idx.iteritems()):
        regions[idx] = {
            'sets': k,
            'elems': v
        }

    return regions


def get_set_region_composition(regions):
    '''
    Map to each input set the set of regions composing it
    Probably O(number of regions)

    'set_region_composition' -
        key: set_id (from input sets)
        value: regions that make up the input set
    '''
    set_region_composition = {}
    for region_id in regions:
        for s_id in regions[region_id]['sets']:
            if s_id not in set_region_composition:
                set_region_composition[s_id] = set()
            set_region_composition[s_id].add(region_id)

    return set_region_composition


def create_graph(adjacency):
    G = gt.Graph(directed=False)
    G.add_vertex(len(adjacency))
    for idx, v in enumerate(adjacency):
        if idx % 1000 == 0 and idx > 0:
            print idx
        for u in adjacency[v]:
            if not G.edge(v, u):
                G.add_edge(v, u)
    # NOTE: Parallel edges will be removed, if any.
    gt.remove_parallel_edges(G)
    return G


def write_graph(G, output_prefix):
    graph_file = output_prefix + '_graph.gt'
    G.save(graph_file)


# TODO: This should be able to alternatively take in adjacency map
def write_adjacency(G, output_prefix):
    adjacency_file = output_prefix + '_adjacency.txt'
    with open(adjacency_file, 'w') as f:
        for v in G.vertices():
            neighbors = [int(n) for n in v.out_neighbours()]
            out_str = '{} ' + ('{} ' * len(neighbors))[:-1] + '\n'
            out_str = out_str.format(int(v), *neighbors)
            f.write(out_str)


def write_regions(regions, output_prefix):
    regions_file = output_prefix + '_regions.pkl'
    with open(regions_file, 'wb') as f:
        pickle.dump(regions, f)


def write_element_associations(elem_assoc, output_prefix):
    elem_assoc_file = output_prefix + '_elem_assoc.pkl'
    with open(elem_assoc_file, 'wb') as f:
        pickle.dump(elem_assoc, f)


if __name__ == '__main__':
    REGION_ADJACENCY_METHODS = {
        'depth-difference': depth_difference,
        'depth-difference-strict': depth_difference_strict,
        'next-highest-depth': next_highest_depth,
    }

    parser = init_argparser()
    args = parser.parse_args()

    input_file = args.input_file
    output_prefix = args.output_prefix
    max_depth_diff = args.max_depth_diff
    connection_type = args.connection_type
    if connection_type not in REGION_ADJACENCY_METHODS:
        raise ValueError('invalid connection type')
    create_region_adjacency = REGION_ADJACENCY_METHODS[connection_type]

    S, elem_assoc = read_sets(input_file)
    regions = find_regions(elem_assoc)
    set_region_composition = get_set_region_composition(regions)
    adjacency = create_region_adjacency(regions, set_region_composition)
    G = create_graph(adjacency)
    print G

    write_graph(G, output_prefix)
    write_adjacency(G, output_prefix)
    write_regions(regions, output_prefix)
    write_element_associations(elem_assoc, output_prefix)
