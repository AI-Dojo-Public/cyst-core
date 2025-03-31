from dataclasses import dataclass, field

from netaddr import IPAddress, IPNetwork
from typing import Union, Optional, List
from uuid import uuid4
from serde import serialize, coerce
from serde.compat import typename

from cyst.api.configuration.configuration import ConfigItem


@serialize(type_check=coerce)
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
    """
    ip: IPAddress = field(metadata={
        'serde_serializer': lambda x: {"cls_type": typename(type(x)), "value": str(x)},
    })
    net: IPNetwork = field(metadata={
        'serde_serializer': lambda x: {"cls_type": typename(type(x)), "value": str(x)},
    })
    index: int = field(default=-1)
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__port"
    id: str = ""


@serialize(type_check=coerce)
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
    """
    ip: IPAddress = field(metadata={
        'serde_serializer': lambda x: {"cls_type": typename(type(x)), "value": str(x)}
    })
    net: IPNetwork = field(metadata={
        'serde_serializer': lambda x: {"cls_type": typename(type(x)), "value": str(x)}
    })
    index: int = field(default=-1)
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__interface"
    id: str = ""


@serialize(type_check=coerce)
@dataclass
class ConnectionConfig(ConfigItem):
    """ Configuration of a network connection.

    Represents a connection between two network ports/interfaces. A connection will in future support setting of
    connection properties, such as delay or packet drops. While the supporting infrastructure is partially present
    in the code now, it is not propagated into the configuration a so, each connection has a unit speed (in terms of
    the simulation time) with zero drops.

    :param src_ref: Connection source configuration or its ref.
    :type src_ref: ConfigItem | str

    :param src_port: The index of a source port/interface.
    :type src_port: int

    :param dst_ref: Connection destination configuration or its ref.
    :type dst_ref: ConfigItem | str

    :param dst_port: The index of a destination port/interface.
    :type dst_port: int
    """
    src_ref: Union[ConfigItem, str]
    src_port: int
    dst_ref: Union[ConfigItem, str]
    dst_port: int
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__connection"
    id: str = ""

    def __post_init__(self):
        if isinstance(self.src_ref, ConfigItem):
            self.src_ref = self.src_ref.ref

        if isinstance(self.dst_ref, ConfigItem):
            self.dst_ref = self.dst_ref.ref

        if not self.src_ref or not self.dst_ref:
            raise RuntimeError(f"Connection configuration can't have an empty source or destination. Source: {self.src_ref}, Destination: {self.dst_ref}.")


@serialize(type_check=coerce)
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
    """
    network: IPNetwork
    port: int
    metric: int = field(default=100)
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__route"
    id: str = ""


@serialize(type_check=coerce)
@dataclass
class SessionConfig(ConfigItem):
    """ Configuration of a session.

    A session represents a virtual connection between two endpoint services that is ignoring the routing limitations
    imposed by routers and firewalls en route.

    :param src_service: A service that the session originates from.
    :type src_service: str

    :param dst_service: A service that the session terminates at.
    :type dst_service: str

    :param waypoints: A list of node IDs through which the session is established.
    :type waypoints: List[str]

    :param reverse: The direction of construction of the session. If reverse is set, then session is originating from
        the destination service. This can matter, because the session creation should honor the router configuration and
        the reverse shell can be the only one that can be established. But, for example, the CYST simulation engine
        tries to construct the session in both ways to see if anything works, so this parameter may be inconsequential.
    :type reverse: bool
    """
    src_service: str
    dst_service: str
    # TODO: Session configuration does not enable chaining through parent-child relation. This may be wanted in some cases.
    waypoints: List[str]
    reverse: bool = False
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__session"
    id: str = ""
