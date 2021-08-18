import queue
import random
from typing import List, Optional
from deprecated import deprecated

import networkx as nx

@deprecated("clustering has been moved to after action mapping, and the logic of it has changed")
class GraphClusterer:
    def __init__(self, graph: nx.DiGraph, cluster_population: int) -> None:
        """

        :param graph: the graph to cluster
        :param cluster_population: maximum entities in one cluster
        """
        self._graph = graph
        self._population = cluster_population
        self._clusters = 1
        self._queue = queue.SimpleQueue()
        self._cluster_queues = {}  # parent: children
        self._actual_population = 0

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    @property
    def population(self) -> int:
        return self._population

    @property
    def clusters(self) -> int:
        return self._clusters

    @clusters.setter
    def clusters(self, value: int) -> None:
        self._clusters = value

    def cluster(self, re_cluster: bool = False) -> List[List[int]]:
        """
        :param re_cluster: whether the graph was clustered before -> needs cleanup
        :return: the graph, where for every node the cluster argument is set
        """
        if re_cluster:
            for node in self.graph:
                self.graph.nodes[node]["cluster"] = 0
        self._cluster()

        res = {}
        for i in range(-1, self._clusters):
            res[i] = []
        for num, node in enumerate(self.graph.nodes(data=True)):
            res[node[1]["cluster"]].append(num)

        return list(res.values())

    def _add_cluster_queue(self, parent: str, nodes: List[str]) -> None:
        """
        Creates a queue of nodes reachable from "parent".

        :param parent: starting node
        :param nodes: children of parent
        :return: NIL
        """
        q = queue.SimpleQueue()
        for e in nodes:
            if self.graph.nodes[e]["cluster"] == 0:
                q.put(e)
        self._cluster_queues[parent] = q

    def _add_to_queue(self, nodes: List[str]) -> None:
        """
        :param nodes: A list of nodes to add to queue of reached nodes
        :return: NIL
        """
        for e in nodes:
            if self.graph.nodes[e]["cluster"] == 0:
                self._queue.put(e)

    def _cluster(self) -> None:
        """
        Initializes the graph and all helping data structures for clustering, calls clustering process.
        :return: NIL
        """
        start = self.graph["start"]
        keys = list(start.keys())
        self._add_to_queue(keys)
        self._add_cluster_queue("start", keys)
        self._make_clusters()


    def _make_clusters(self) -> None:
        """
        Keeps making clusters until every node is a part of one.
        :return:  NIL
        """
        while not self._queue.empty():  # unprocessed nodes remain
            start_node = self._queue.get()
            if self.graph.nodes[start_node]["cluster"] != 0:  # not yet in cluster
                continue
            self._make_cluster(start_node)

    def _make_cluster(self, start_node: str) -> None:
        """
        Creates one cluster.

        :param start_node: node to start the new cluster from
        :return: NIL
        """
        if len(self._cluster_queues) > 1:  # new cluster started, this had to be cleared beforehand
            raise RuntimeError("something wrong with traversal")
        self._advance(start_node, None, True)

    def _advance(self, start_node: Optional[str], parent_node: Optional[str], verbose_dfs: bool = False) -> None:
        """
        Populates the actual cluster, or closes it and starts a new if needed.

        :param start_node: the node to put into a cluster
        :param parent_node: the node last processed
        :param verbose_dfs: True if we force the algorithm to use advancing in depth

        :return: NIL
        """
        if start_node is None:  # the cluster can not grow as all nodes reachable from it are already taken
            self._actual_population = 0
            self.clusters += 1
            self._cluster_queues.clear()
            return self._make_clusters()
            # clear temporary data and proceed with the next node reached but unclustered

        if self._actual_population >= self._population:  # cant grow because we would exceed population limit
            self._cluster_queues.clear()
            self.clusters += 1
            self._actual_population = 0
            if parent_node is not None:
                self._add_cluster_queue(parent_node, list(self.graph[parent_node].keys()))
            return self._make_cluster(start_node)
        # clear temporary data, if possible initialize it for next cluster, and proceed
        # making a new cluster from the start node

        # else chose which advancing technique to use, and call it
        rand = random.randint(0, 9)
        if verbose_dfs or rand < 7:
            self._advance_dfs(start_node)
        else:
            self._advance_bfs(start_node)

    def _advance_dfs(self, start_node: str, from_bfs: bool = False) -> None:
        """
        Implements a way of populating the cluster, advancing in depth.

        :param start_node: the actual node to put into the actual cluster
        :param from_bfs: whether this method was called from the other - means the other failed to find a usable node
        :return: NIL
        """
        self.graph.nodes[start_node]["cluster"] = self.clusters
        reachable = list(self.graph[start_node].keys())  # the next node is from the children
        if not from_bfs:  # otherwise this is already done
            self._actual_population += 1
            self._add_to_queue(reachable)
        self._add_cluster_queue(start_node, reachable)  # filters those in a cluster already
        usable = self._cluster_queues[start_node]
        if usable.empty():  # if we cant find the next node this way, try the other method iff the call to this method
            # is not because of its failure
            # otherwise proceed with a new cluster
            return self._advance_bfs(start_node, True) if not from_bfs else self._advance(None, None)
        self._advance(usable.get(), start_node)  # proceed with chosen heir

    def _advance_bfs(self, start_node: str, from_dfs: bool = False) -> None:
        """
        Implements a way of populating the cluster, advancing in breadth.

        :param start_node: the actual node to put into the actual cluster
        :param from_dfs: whether this method was called from the other - means the other failed to find a usable node
        :return: NIL
        """
        self.graph.nodes[start_node]["cluster"] = self.clusters
        if not from_dfs:  # otherwise done already
            self._actual_population += 1
            reachable = list(self.graph[start_node].keys())
            self._add_to_queue(reachable)
        usable = None
        parent = None
        keys = list(self._cluster_queues.keys())  # nodes that are parents of at least one node of the cluster
        random.shuffle(keys)
        for e in keys:  # randomly iterate them, find one that has at least one unclustered children
            if not self._cluster_queues[e].empty():
                parent = e
                usable = self._cluster_queues[e]
                break
        if usable is None:  # if you cant find such, try the other method, iff the reason of calling this method is not
            # the others failure
            # otherwise proceed with new cluster
            return self._advance_dfs(start_node, True) if not from_dfs else self._advance(None, None)
        self._advance(usable.get(), parent)  # proceed with chosen node
