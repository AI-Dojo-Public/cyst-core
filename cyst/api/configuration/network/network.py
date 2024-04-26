from dataclasses import dataclass, field
from typing import List, Union
from uuid import uuid4
from serde import serialize

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.network.elements import ConnectionConfig
from cyst.api.configuration.network.node import NodeConfig
from cyst.api.configuration.network.router import RouterConfig

# TODO: Useless - remove
@serialize
@dataclass
class NetworkConfig(ConfigItem):
    """ Configuration of a network.

    A network is a collection of nodes linked by connections. The configuration enables creation of unconnected subnets,
    but to make any use of it, there needs to be added a set of actions, which enable setting up/tearing down of
    connections.

    :param nodes: A collection of nodes and routers that constitute the vertices of network topology.
    :type nodes: List[Union[NodeConfig, RouterConfig, str]]

    :param connections: A collection of connections that constitute the edges of network topology.
    :type connections: List[Union[ConnectionConfig, str]]

    :param id: A unique identifier of the network configuration.
    :type id: str
    """
    nodes: List[Union[NodeConfig, RouterConfig, str]]
    connections: List[Union[ConnectionConfig, str]]
    id: str = field(default_factory=lambda: str(uuid4()))
