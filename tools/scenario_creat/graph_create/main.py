from tools.scenario_creat.graph_create.graph_builder import GraphBuilder
from tools.scenario_creat.graph_create.graph_clusterer import GraphClusterer
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime

def main():
    print("build start: ", datetime.now())
    gb = GraphBuilder("aim", 5, 3, 3, 2, 2, 40, 4)
    graph = gb.build()
    print("build end: ", datetime.now())
    counter = 1
    color_map = []
    for node in graph:
        color_map.append("pink" if not graph.nodes[node] else graph.nodes[node]["color"] )
        # start node is yellow
        # target node is red
        # nodes of the successful paths are blue
        # random nodes from fan-in are orange
        # random nodes from fan-out are purple

    edges = set()
    paths = nx.all_simple_paths(graph, "start", "aim")
    for path in map(nx.utils.pairwise, paths):
        for edge in path:
            edges.add(edge)

    edge_map = []
    for edge in graph.edges():
        edge_map.append("green" if edge in edges else "grey")

   # nx.draw_kamada_kawai(graph, node_size=25, node_color=color_map, edge_color=edge_map, width=1)
    #plt.show()
    print("cluster start: ", datetime.now())
    gc = GraphClusterer(graph, 7)
    clusters = gc.cluster()
    print("cluster end: ", datetime.now())
    print(clusters)
    labels = dict((n, d["cluster"]) for n,d in graph.nodes(data=True))
    nx.draw_kamada_kawai(graph, node_size=25, node_color=color_map, edge_color=edge_map, width=1, labels=labels)
    plt.show()
    print(graph.nodes)
    mat = nx.to_numpy_matrix(graph)
    mat2 = nx.to_dict_of_dicts(graph)
    print(mat)


if __name__ == '__main__':
    main()
