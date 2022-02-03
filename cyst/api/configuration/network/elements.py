from dataclasses import dataclass, field

from netaddr import IPAddress, IPNetwork
from typing import Optional
from uuid import uuid4
from tools.serde_customized import serialize

from cyst.api.configuration.configuration import ConfigItem
from tools.serde_customized.compat import typename


@serialize
@dataclass
class PortConfig(ConfigItem):
    """ Configuration of a network port.

    A network port represents an abstraction of an ethernet port, with a given IP address and a given network. A network
    port does not support a default routing through a gateway and so it is used mostly for routers, which maintain
    their own routing tables based on the port indexes.

    :param ip: The assigned IP address of the port.
    :type ip: IPAddress

    :param net: The assigned network of the port. If used only for inter-router communication, ip/32 or ip/128
        can be used.
    :type net: IPNetwork

    :param index: The index of the port. The index is used for unique addressing of a port within a node, especially
        for correctly setting routing tables. If left at the default value, it is assigned the next free index.
    :type index: int

    :param id: A unique identifier of the port configuration.
    :type id: str
    """
    ip: IPAddress = field(metadata={
        'serde_serializer': lambda x: {"cls_type": typename(type(x)), "value": str(x)},
    })
    net: IPNetwork = field(metadata={
        'serde_serializer': lambda x: {"cls_type": typename(type(x)), "value": str(x)},
    })
    index: int = field(default=-1)
    id: str = field(default_factory=lambda: str(uuid4()))


@serialize
@dataclass
class InterfaceConfig(ConfigItem):
    """ Configuration of a network interface.

    A network interface represents an abstraction of an ethernet port, with a given IP address and a given network.
    A network interface automatically calculates the gateway and therefore enables a seamless networking.

    :param ip: The assigned IP address of the interface.
    :type ip: IPAddress

    :param net: The assigned network of the interface.
    :type net: IPNetwork

    :param index: The index of the interface. The index is used for unique addressing of an interface within a node. If
        left at the default value, it is assigned the next free index.
    :type index: int

    :param id: A unique identifier of the interface configuration.
    :type id: str
    """
    ip: IPAddress = field(metadata={
        'serde_serializer': lambda x: {"cls_type": typename(type(x)), "value": str(x)}
    })
    net: IPNetwork = field(metadata={
        'serde_serializer': lambda x: {"cls_type": typename(type(x)), "value": str(x)}
    })
    index: int = field(default=-1)
    id: str = field(default_factory=lambda: str(uuid4()))


@serialize
@dataclass
class ConnectionConfig(ConfigItem):
    """ Configuration of a network connection.

    Represents a connection between two network ports/interfaces. A connection will in future support setting of
    connection properties, such as delay or packet drops. While the supporting infrastructure is partially present
    in the code now, it is not propagated into the configuration a so, each connection has a unit speed (in terms of
    the simulation time) with zero drops.

    :param src_id: The id of a source node.
    :type src_id: str

    :param src_port: The index of a source port/interface.
    :type src_port: int

    :param dst_id: The id of a destination node.
    :type dst_id: str

    :param dst_port: The index of a destination port/interface.
    :type dst_port: int

    :param id: A unique identifier of the connection configuration.
    :type id: str
    """
    src_id: str
    src_port: int
    dst_id: str
    dst_port: int
    id: str = field(default_factory=lambda: str(uuid4()))


@serialize
@dataclass
class RouteConfig(ConfigItem):
    """ Configuration of a network route.

    A route specifies which port should the traffic to specific network be routed through. Many routes can be specified
    for a node. If there is an overlap in network specification, than the resulting port is selected according to the
    route metrics (i.e., the lower the metric the higher the chance to be selected as the route). In case of a metric
    equality, the most specific network is selected.

    :param network: A network this route is related to.
    :type network: IPNetwork

    :param port: A port/interface index, where to route traffic to the particular network.
    :type port: int

    :param metric: A route metric used for deciding which route to use in case of network overlap.
    :type metric: int

    :param id: A unique identifier of the route configuration.
    :type id: str
    """
    network: IPNetwork
    port: int
    metric: int = field(default=100)
    id: str = field(default_factory=lambda: str(uuid4()))
