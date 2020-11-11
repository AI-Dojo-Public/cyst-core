import random
from typing import List, Dict, Tuple

import networkx as nx

def flip(prob: float) -> bool:
    delim = int(prob * 100)
    gen = random.randint(1, 100)
    return True if gen <= delim else False

class Clusterer(object):
    def __init__(self, graph: nx.DiGraph, mappings: Dict[int, Tuple[int,int]], prob: float) -> None:
        self._graph = graph
        self._mappings = mappings
        self._clusters = 0
        self._epsilon = 0.9
        self._base_prob = prob
        self._translator = {}
        for num, node in enumerate(self._graph.nodes):
            self._translator[node] = num

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    @property
    def clusters(self) -> int:
        return self._clusters

    ### API ###
    def cluster(self) -> List[List[int]]:
        self._cluster()

        res = {}
        for i in range(0, self._clusters+1):
            res[i] = []
        for num, node in enumerate(self.graph.nodes(data=True)):
            res[node[1]["cluster"]].append(num)

        return list(res.values())

    ### IMPLEMENTRATION ###
    def _cluster(self) -> None:
        """
        Initializes the graph and all helping data structures for clustering, calls clustering process.
        :return: NIL
        """
        self._make_clusters()


    def _make_clusters(self) -> None:
        """
        Keeps making clusters until every node is a part of one.
        :return:  NIL
        """

        self._make_cluster("start")

    def _make_cluster(self, start_node: str) -> None:
        """
        Creates one cluster.

        :param start_node: node to start the new cluster from
        :return: NIL
        """
        self._clusters += 1
        self._advance(start_node, [], self._clusters, [0])

    def _advance(self, node: str, services: List[int], cluster_id: int, population: List[int]): # population is List because python copies simple ints, but i need changes when recursion returns, long live pointers and references

        self.graph.nodes[node]["cluster"] = cluster_id
        population[0] += 1
        services.append(self._mappings[self._translator[node]][0])

        reachable = list(self.graph[node].keys())
        for e in reachable:
            coin = flip(self._base_prob * (self._epsilon**population[0]))
            if self._mappings[self._translator[e]][0] in services or not coin:
                self._make_cluster(e)
            else:
                self._advance(e, services, cluster_id, population)
