import math
import random
from enum import IntEnum
from typing import Dict, List, Tuple, Set, Any

import networkx as nx


class EntryDeg(IntEnum):
    IN = 0,
    OUT = 1


class GraphBuilder:
    def __init__(self, aim: str, shortest_lim: int, o_deg: int, i_deg: int, aim_ch_num: int, min_paths: int,
                 min_nodes: int, layer_max: int) -> None:
        """

        :param aim: the target node's name
        :param shortest_lim: length of the shortest path to create
        :param o_deg: maximum out degree for all nodes except root
        :param i_deg: maximum in degree foscenario_creatr all nodes
        :param aim_ch_num: number of nodes within 1 hop of target node
        :param min_paths: minimal number of paths in the graph (from root to target)
        :param min_nodes: minimal number of nodes
        :param layer_max: maximal number of nodes in each layer
        """
        self._aim = aim
        self._o_deg = o_deg
        self._i_deg = i_deg
        self._spl = shortest_lim
        self._aim_ch_num = aim_ch_num
        self._min_nodes = min_nodes
        self._path_count = random.randint(min_paths, 2 * min_paths)  # on path creation subtract 1
        self._node_num = 0
        self._graph = None
        self._layers = math.ceil(1.5 * self._spl)  # number of layers to use
        self._nodes = {}
        for i in range(0, self._layers):
            self.nodes[i] = {}
        self._has_minimal = False
        self._random_counter = 0
        self._layer_max_node = layer_max

    @property
    def aim(self) -> str:
        return self._aim

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    @property
    def out_deg(self) -> int:
        return self._o_deg

    @property
    def in_deg(self) -> int:
        return self._i_deg

    @property
    def shortest_path_limit(self) -> int:
        return self._spl

    @property
    def aim_child_num(self) -> int:
        return self._aim_ch_num

    @property
    def nodes(self) -> Dict[int, Dict[int, List[int]]]:
        return self._nodes

    @graph.setter
    def graph(self, value: nx.Graph) -> None:
        self._graph = value

    ### API ###
    def build(self) -> nx.DiGraph:
        """
        :return: a full pseudo-random (empty) attack graph
        """
        self.graph = nx.DiGraph()
        self.graph.add_node("start", color="yellow", cluster=-1)
        self.graph.add_node(self.aim, color="red", cluster=-1)
        self._build()
        return self.graph


    ### IMPLEMENTATION ###
    def _add_node(self, layer: int, num: int, color: str = "blue") -> str:
        """
        Adds one node to the graph and handles all changes that need to be done.

        :param layer: part of nodes name
        :param num: part of nodes name
        :param color: shows node's origin
        :return: the name of the node, with which it can be found in the networkx object
        """
        name = "l{}n{}".format(layer, num)
        if self.nodes[layer].get(num, None) is None:
            self.graph.add_node(name, color=color, cluster=0)
            self._nodes[layer][num] = [0, 0]
            self._node_num += 1
        return name

    def _add_edge(self, layer_from: int, num_from: int, layer_to: int, num_to: int) -> None:
        """
        Creates an edge between the two nodes given, handles all needed changes.

        :param layer_from: node identification (1)
        :param num_from: node identification   (1)
        :param layer_to: node identification   (2)
        :param num_to: node identification     (2)
        :return: NIL
        """
        self.graph.add_edge(
            "l{}n{}".format(layer_from, num_from),
            "l{}n{}".format(layer_to, num_to))
        self.nodes[layer_from][num_from][EntryDeg.OUT] += 1
        self.nodes[layer_to][num_to][EntryDeg.IN] += 1

    def _build(self) -> None:
        """
        Wraps the calls of separate processes taking part in graph creation

        :return: NIL
        """
        for i in range(0, self.aim_child_num):
            node = self._add_node(0, i)
            self.graph.add_edge(node, self.aim)
            self.nodes[0][i][EntryDeg.OUT] += 1
            self._add_path(0, i, random.randint(self.shortest_path_limit, self._layers - 1))
        self._add_minimal_path()
        self._add_paths()
        self._add_random()

    def _add_minimal_path(self) -> None:
        """
        Creates the shortest path needed.

        :return: NIL
        """
        self._add_path(0, random.randint(0, self.aim_child_num - 1), self.shortest_path_limit)

    def _add_random(self) -> None:
        """
        Until the graph does not include enough nodes, add random nodes.

        :return: NIL
        """
        self.nodes[-1] = {}
        while self._node_num < self._min_nodes:
            self._fan_in_fan_out()

    def _fan_in_fan_out(self) -> None:
        """
        Chose which method should add random nodes, both have the probability 1/2

        :return: NIL
        """
        rand = random.randint(0, 9)
        if rand < 5:
            self._fan_in()
        else:
            self._fan_out()

    def _add_paths(self) -> None:
        """
        Adds new paths until the minimum quantity is reached

        :return: NIL
        """
        tries = 2 * self._path_count
        while self._path_count > 0 and tries > 0:  # no infinite loop if we somehow cannot create the needed amount
            self._add_path(0, random.randint(0, self.aim_child_num - 1),
                           random.randint(self.shortest_path_limit, self._layers - 1))
            tries -= 1

    def _add_path(self, from_layer: int, from_node: int, path_len: int) -> None:
        """
        Create one full path.

        :param from_layer: always layer 0 (nodes within 1 hop from target)
        :param from_node: exact node
        :param path_len: predestined random path length
        :return:  NIL
        """
        usable = list(self.nodes.keys())
        usable.remove(0)
        use_layers = sorted(random.sample(usable, path_len))  # choose which layers will be used for this path
        if path_len == self.shortest_path_limit:
            self._has_minimal = True
        # start creating the path level-by-level
        self._create_level(from_layer, from_node, use_layers, 0, (0, random.randint(1, self._layer_max_node)), True)

    def _create_level(self, layer_from: int, node_from: int, layers: List[int], index: int,
                      branching_limits: Tuple[int, Any], verbose: bool = False) -> bool:
        """
        Create one hop of a path

        :param layer_from: node identification
        :param node_from: node identification
        :param layers: list of layers to use
        :param index: index into layers param, keeping track of where we are actually
        :param branching_limits: a sub-interval of the layers nodes to be preferred to be chosen for edge creation
        :param verbose: True if the actual node is not reachable from the root, in this case creating edges with nodes
                        exceeding their out degree might happen
        :return: True if building is successful a.k.a the actual node got reachable from the root
        """
        if index < 0:
            return True
        if index >= len(layers):  # end of path, just connect with root
            self.graph.add_edge("start", "l{}n{}".format(layer_from, node_from))
            self.nodes[layer_from][node_from][EntryDeg.IN] += 1
            self._path_count -= 1
            return True
        children = set()
        counter = 0
        while not children:  # might happen that no children are usable
            if counter >= 2:
                break
            children = self._fill_children(layer_from, node_from, layers[index], branching_limits, verbose)
            counter += 1
        retval = self.nodes[layer_from][node_from][EntryDeg.IN] != 0  # if a child is already present we are good to go
        new_verbose = True
        for e in children:
            new_verbose = new_verbose and (False if self.nodes[layers[index]].get(e, None) is not None and
                                           self.nodes[layers[index]][e][EntryDeg.OUT] != 0 else True)
            # for the next level be verbose only of all "children" are unused (0 out degree means no in edge)
        for e in children:
            self._add_node(layers[index], e)
            if self._create_level(layers[index], e, layers, index + 1, (0, random.randint(1, self._layer_max_node))
                                  , new_verbose):  # connect if child is reachable from root
                self._add_edge(layers[index], e, layer_from, node_from)
                retval = True  # at least on child must be created/ connected
            elif self.nodes[layers[index]][e][EntryDeg.OUT] == 0 and self.nodes[layers[index]][e][EntryDeg.IN] == 0:
                self._remove_node(layers[index], e)  # no unreachable nodes will appear in the graph
        return retval

    def _fill_children(self, layer_from: int, node_from: int, layer_to: int, branching_limits: Tuple[int, Any],
                       verbose: bool) -> Set[int]:
        """
        Helps with the choice of nodes to connect to

        :param layer_from: node identifier
        :param node_from: node identifier
        :param layer_to: layer to chose nodes from for connecting
        :param branching_limits: interval of nodes to prefer
        :param verbose: whether to choose nodes that exceed their out degree
        :return:  Set of nodes to try connecting to
        """
        children = set()
        diff = self.in_deg - self.nodes[layer_from][node_from][EntryDeg.IN]
        if diff <= 0:
            return children
        child_num = random.randint(1, diff)
        try:
            limit_low = random.randint(branching_limits[0], branching_limits[1] - child_num)
            limit_high = random.randint(limit_low + child_num, branching_limits[1])
        except ValueError:
            limit_low = 0
            limit_high = random.randint(0, branching_limits[1])
        for i in range(0, child_num):
            rand = random.randint(limit_low, limit_high)
            target = self.nodes[layer_to].get(rand, None)
            if target is None or target[
                    EntryDeg.OUT] < self.out_deg or verbose:  # THIS MIGHT BE GOOD HERE, out degrees should be used for
                # the random ballast, in the good graph they might be ok without -- ASK
                children.add(rand)
        return children

    def _remove_node(self, layer: int, num: int) -> None:
        """
        Removes a node from the graph, handles all changes needed

        :param layer: identifier
        :param num: identifier
        :return: NIL
        """
        self.graph.remove_node("l{}n{}".format(layer, num))
        self.nodes[layer].pop(num)
        self._node_num -= 1

    def _fan_in(self) -> None:
        """
        Adding random nodes with the fan in method ->
        Creates a new node and randomly connects existing one to it.

        :return: NIL
        """
        node = self._add_node(-1, self._random_counter, "orange")
        used = []
        cycle_counter = 0
        counter = 0
        while counter <= self.in_deg:
            if cycle_counter >= 10:
                break
            try:
                target_layer = random.choice(list(self.nodes.keys()))
                target_node = random.choice(list(self.nodes[target_layer].keys()))
            except IndexError:
                cycle_counter += 1
                continue
            if "l{}n{}".format(target_layer, target_node) != node and (target_layer, target_node) not in used:
                used.append((target_layer, target_node))
                if self.nodes[target_layer][target_node][EntryDeg.OUT] < self.out_deg:
                    self._add_edge(target_layer, target_node, -1, self._random_counter)
                    counter += 1
            cycle_counter += 1

        if counter == 0:
            self._remove_node(-1, self._random_counter)
        self._random_counter += 1

    def _fan_out(self) -> None:
        """
        Adding random nodes with the fan out method ->
        Chooses an existing node, and adds as many new nodes, as its remaining out degree allows,
        connects the chosen to the new

        :return: NIL
        """
        try:
            target_layer = random.choice(list(self.nodes.keys()))
            target_num = random.choice(list(self.nodes[target_layer].keys()))
        except IndexError:
            self._fan_out()
            return
        diff = self.out_deg - self.nodes[target_layer][target_num][EntryDeg.OUT]
        for i in range(0, diff):
            self._add_node(-1, self._random_counter, "purple")
            self._add_edge(target_layer, target_num, -1, self._random_counter)
            self._random_counter += 1
