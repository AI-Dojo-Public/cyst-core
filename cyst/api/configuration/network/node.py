import dataclasses
from dataclasses import dataclass, field
from typing import List, Union, Optional
from uuid import uuid4
from serde import serialize

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.host.service import ActiveServiceConfig, PassiveServiceConfig
from cyst.api.configuration.network.elements import InterfaceConfig
from cyst.api.configuration.network.firewall import FirewallConfig


@dataclass
class NodeConfig(ConfigItem):
    """ Configuration for a network node

    A network node is a main building block of simulation topology. It is modelled as a collection of services and a
    set of network interfaces.

    :param active_services: A list of active services running on the node.
    :type active_services: List[Union[ActiveServiceConfig, str]]

    :param passive_services: A list of passive services running on the node.
    :type passive_services: List[Union[PassiveServiceConfig, str]]

    :param traffic_processors: A list of either active services that are acting as traffic processors, or at most one
        firewall.
    :type traffic_processors: Optional[List[Union[FirewallConfig, ActiveServiceConfig, str]]]

    :param shell: A name of a passive service that is designated as a shell. Properties of the shell service determine
        the impact of some exploits, e.g., when related to access rights. Technically, any name could be selected as a
        shell, because the system currently does not check whether the service exists or not.
    :type shell: str

    :param interfaces: A list of interfaces on the node.
    :type interfaces: List[Union[InterfaceConfig, str]]
    """
    active_services: List[Union[ActiveServiceConfig, str]]
    passive_services: List[Union[PassiveServiceConfig, str]]
    traffic_processors: List[Union[FirewallConfig, ActiveServiceConfig, str]]
    shell: str
    interfaces: List[Union[InterfaceConfig, str]]
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__node"
    id: str = ""
