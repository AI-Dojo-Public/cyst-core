from dataclasses import dataclass, field
from typing import List, Union, Optional
from uuid import uuid4
from serde import serialize

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.host.service import ActiveServiceConfig
from cyst.api.configuration.network.elements import InterfaceConfig, RouteConfig
from cyst.api.configuration.network.firewall import FirewallConfig


@serialize
@dataclass
class RouterConfig(ConfigItem):
    """ Configuration of a network router

    Router models an active network device that forwards messages over the network according to rules. At the conceptual
    level it conflates the concept of switch and router to one device.

    Currently a router is implemented as a special type of node, with distinct code paths, in the future it is expected
    that a router would be implemented as an active service on a node. This will enable better logical separation
    between its routing, firewalling, and IDS/IPS activities. It will also be more fit for SDN modelling.

    :param interfaces: A list of network interfaces.
    :type interfaces: List[Union[InterfaceConfig]]

    :param traffic_processors: A list of either active services that are acting as traffic processors, or at most one
        firewall. Firewall is used as a mechanism for router to do inter-network routing, by means of a FORWARD chain.
    :type traffic_processors: Optional[List[Union[FirewallConfig, ActiveServiceConfig, str]]]

    :param routing_table: A routing configuration for inter-router communication. Routing to end devices is arranged
        automatically when creating connections between end devices and the router. Networks are inferred from
        interface configurations.
    :type routing_table: List[RouteConfig]

    :param firewall: A configuration of firewall rules.
    :type firewall: Optional[FirewallConfig]

    :param id: A unique identifier of the router configuration.
    :type id: str
    """
    interfaces: List[Union[InterfaceConfig]]
    traffic_processors: List[Union[FirewallConfig, ActiveServiceConfig, str]]
    routing_table: List[RouteConfig] = field(default_factory=list)  # TODO: check if such a default is ok
    id: str = field(default_factory=lambda: str(uuid4()))
