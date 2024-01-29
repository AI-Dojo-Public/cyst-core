import networkx as nx

from abc import ABC, abstractmethod
from netaddr import IPAddress
from typing import Optional, List, Dict

from cyst.api.environment.configuration import GeneralConfiguration
from cyst.core.network.elements import Connection, ConnectionImpl, Hop, Endpoint, Resolver, InterfaceImpl
from cyst.core.network.router import Router
from cyst.core.network.node import NodeImpl


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
