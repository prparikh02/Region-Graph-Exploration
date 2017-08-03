import argparse
import graph_tool.all as gt
import app.TreeExploration as TreeExploration


def init_argparser():
    description = ('Given a graph, G (graph_tool.Graph), create and save '
                   'a HierarchyTree. A HierarchyTree attempts to recursively '
                   'partition the input graph using a variety of partioning '
                   'methods.')
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('input_file', metavar='i', type=str,
                        help='input path of graph file (.gt extension)')

    parser.add_argument('output_file', metavar='o', type=str,
                        help='output path of tree file')

    parser.add_argument('-t', '--threshold', type=int, dest='threshold',
                        default=256,
                        help='a TreeNode that has greater than \'threshold\' '
                             'number of vertices will be attempted to be '
                             'partitioned')

    parser.add_argument('-k', '--keep-peel-one', action='store_false',
                        dest='separate_peel_one',
                        help='prevents removal (partitioning) of peel 1 '
                             'vertices as the first step of partitioning')

    parser.add_argument('-c', '--check-partition', action='store_true',
                        dest='check_partition',
                        help='check integrity of node partitioning (primarily '
                             'for debugging purposes)')

    return parser

if __name__ == '__main__':
    parser = init_argparser()
    args = parser.parse_args()
    optional_args = ['threshold', 'separate_peel_one', 'check_partition']
    kwargs = {k: getattr(args, k) for k in optional_args}

    G = gt.load_graph(args.input_file)
    TE = TreeExploration.TreeExploration(G)
    root = TE.create_root()
    TE.explore_tree(root=root, **kwargs)
    TE.save_tree(args.output_file)
