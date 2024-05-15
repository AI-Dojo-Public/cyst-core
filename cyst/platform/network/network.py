import networkx as nx

from abc import ABC, abstractmethod
from netaddr import IPAddress
from typing import Optional, List, Dict, Union
from itertools import product

from cyst.api.environment.configuration import GeneralConfiguration
from cyst.api.network.node import Node

from cyst.platform.network.elements import Connection, ConnectionImpl, Hop, Endpoint, Resolver, InterfaceImpl
from cyst.platform.network.router import Router
from cyst.platform.network.node import NodeImpl
from cyst.platform.network.session import Session, SessionImpl


# TODO: The network is largely useless after moving the object store into configuration. I should probably think about
#       whether to keep it or not
class Network(Resolver):
    def __init__(self, conf: GeneralConfiguration):
        self._graph = nx.Graph()
        self._conf = conf

    def add_node(self, node: NodeImpl) -> None:
        # Ignore already present nodes
        if self._graph.has_node(node.id):
            return

        self._graph.add_node(node.id)

    def add_connection(self, n1: NodeImpl, n1_port_index: int, n2: NodeImpl, n2_port_index: int, net: str, connection: Optional[Connection] = None) -> Connection:
        if not n1 or not n2:
            raise Exception("Could not add connection between nonexistent nodes")

        if not connection:
            connection = ConnectionImpl()

        success = True
        result = None
        if isinstance(n1, Router):
            if isinstance(n2, Router):
                success, result = n1._connect_router(n2, connection, n2_port_index, n1_port_index)
                if success:
                    n2_port_index, n1_port_index = result
            else:
                success, result = n1._connect_node(n2, connection, n1_port_index, n2_port_index, net)
                if success:
                    n1_port_index, n2_port_index = result
        elif isinstance(n2, Router):
            success, result = n2._connect_node(n1, connection, n2_port_index, n1_port_index, net)
            if success:
                n2_port_index, n1_port_index = result
        # Direct connection
        else:
            InterfaceImpl.cast_from(n1.interfaces[n1_port_index]).connect_endpoint(
                Endpoint(n2.id, n2_port_index, n2.interfaces[n2_port_index].ip), connection)
            InterfaceImpl.cast_from(n2.interfaces[n2_port_index]).connect_endpoint(
                Endpoint(n1.id, n1_port_index, n1.interfaces[n1_port_index].ip), connection)

        if not success:
            raise Exception("Could not add connection between nodes {} and {}. Reason: {}".format(n1.id, n2.id, result))

        connection.hop = Hop(Endpoint(n1.id, n1_port_index, n1.interfaces[n1_port_index].ip),
                             Endpoint(n2.id, n2_port_index, n2.interfaces[n2_port_index].ip))
        self._graph.add_edge(n1.id, n2.id)

        return connection

    def get_node_by_id(self, id: str = "") -> Optional[NodeImpl]:
        if not id:
            return None
        else:
            return self._conf.get_object_by_id(id, NodeImpl)

    def reset(self) -> None:
        # self._nodes_by_id.clear()
        self._graph.clear()

    def resolve_ip(self, id: str, port: int) -> IPAddress:
        node = self.get_node_by_id(id)
        if not node:
            raise ValueError("Nonexistent node id provided for resolving")

        if port >= len(node.interfaces):
            raise ValueError("Nonexistent port id provided for resolving")

        return node.interfaces[port].ip

    # When creating sessions from nodes, there are two options - either nodes are connected directly, or they
    # go through a router. So correct hops are evaluated either in N-R*-N form or N-N
    # TODO: If one direction fails, session should try constructing itself in reverse order and then restructure hops
    #       so that the origin is always at the first waypoint.
    def create_session(self, owner: str, waypoints: List[Union[str, Node]], src_service: Optional[str],
                        dst_service: Optional[str], parent: Optional[Session], reverse: bool) -> Session:
        path: List[Hop] = []
        source: NodeImpl
        session_reversed = False

        if len(waypoints) < 2:
            raise ValueError("The session path needs at least two ids")

        session_constructed = True
        for direction in ("forward", "reverse"):

            if direction == "reverse":
                if not session_constructed:
                    path.clear()
                    waypoints.reverse()
                    session_reversed = True
                    session_constructed = True
                else:
                    break

            i = 0
            while i < len(waypoints) - 1:
                # There was an error in partial session construction
                if not session_constructed:
                    break

                node0 = None
                node1 = None
                node2 = None

                def get_node_from_waypoint(self, i: int) -> Node:
                    if isinstance(waypoints[i], str):
                        node = self.get_node_by_id(waypoints[i])
                    else:
                        node = waypoints[i]
                    return node

                # Get the nodes
                node0 = get_node_from_waypoint(self, i)
                node1 = get_node_from_waypoint(self, i + 1)

                routers = []
                # N-R*-N
                if node1.type == "Router":
                    router = Router.cast_from(node1)

                    routers.append(router)
                    node2 = get_node_from_waypoint(self, i + len(routers) + 1)

                    while node2.type == "Router":
                        routers.append(Router.cast_from(node2))
                        node2 = get_node_from_waypoint(self, i + len(routers) + 1)

                    path_candidate: List[Hop] = []
                    for elements in product(node0.interfaces, node2.interfaces):
                        node0_iface = InterfaceImpl.cast_from(elements[0])
                        node2_iface = InterfaceImpl.cast_from(elements[1])

                        path_candidate.clear()

                        # Check if the next router is connected to the first node
                        if node0_iface.endpoint.id != routers[0].id:
                            continue

                        # It is, so it's a first hop
                        path_candidate.append(
                            Hop(Endpoint(NodeImpl.cast_from(node0).id, node0_iface.index, node0_iface.ip),
                                node0_iface.endpoint))

                        # Check for every router if it routes the source and destination
                        for j, r in enumerate(routers):
                            # Find if there is a forward port
                            # Ports are returned in order of priority: local IPs, remote IPs sorted by specificity (CIDR)
                            port = r.routes(node0_iface.ip, node2_iface.ip, "*")

                            # No suitable port found, try again
                            if not port:
                                break

                            path_candidate.append(Hop(Endpoint(r.id, port.index, port.ip), port.endpoint))

                        if len(path_candidate) == len(routers) + 1:
                            path.extend(path_candidate)
                            break

                    i += len(routers) + 1

                    if len(path) < i:
                        session_constructed = False
                        break
                        # raise RuntimeError("Could not find connection between {} and {} to establish a session".format(NodeImpl.cast_from(node0).id, NodeImpl.cast_from(node2).id))
                else:
                    # N-N
                    for iface in node0.interfaces:
                        node0_iface = InterfaceImpl.cast_from(iface)

                        if node0_iface.endpoint.id == NodeImpl.cast_from(node1).id:
                            path.append(Hop(Endpoint(NodeImpl.cast_from(node0).id, node0_iface.index, node0_iface.ip),
                                            node0_iface.endpoint))
                            break

                    i += 1
                    if len(path) < i:
                        session_constructed = False
                        break
                        # raise RuntimeError("Could not find connection between {} and {} to establish a session".format(NodeImpl.cast_from(node0).id, NodeImpl.cast_from(node1).id))

        if not session_constructed:
            # Sessions are always tried to be constructed in both directions, so we need to reverse the waypoints again
            waypoints.reverse()
            raise RuntimeError(
                "Could not find connection between the following waypoints to establish a session".format(waypoints))  # MYPY: Missing the parameter in string

        # If the session was constructed from the end to front, we need to reverse the path
        if session_reversed:
            path.reverse()
            for i in range(0, len(path)):
                path[i] = path[i].swap()

        return SessionImpl(owner, parent, path, src_service, dst_service, self)  # MYPY: Services can be None, they are optional
