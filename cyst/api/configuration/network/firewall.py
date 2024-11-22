from dataclasses import dataclass, field
from typing import List
from uuid import uuid4
from serde import serialize

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.network.firewall import FirewallRule, FirewallChainType, FirewallPolicy


@serialize
@dataclass
class FirewallChainConfig(ConfigItem):
    """ Configuration of firewall chain.

    A firewall chain represents a set of rules that are applied to a network traffic.

    :param type: A type of traffic this chain applies to.
    :type type: FirewallChainType

    :param policy: A default policy applied to a traffic, which does not satisfy any rule.
    :type policy: FirewallPolicy

    :param rules: A set of rules governing what happens with a network traffic.
    :type rules: List[FirewallRule]
    """
    type: FirewallChainType
    policy: FirewallPolicy
    rules: List[FirewallRule]
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__firewall_chain"
    id: str = ""


@serialize
@dataclass
class FirewallConfig(ConfigItem):
    """ Configuration of a firewall.

    Firewall is represented as a collection of chains, with a default policy that is applied, unless specified
    otherwise.

    :param default_policy: A default policy applied to a traffic, which is not handled by a chain with its own policy.
    :type default_policy: FirewallPolicy

    :param chains: A list of firewall chain configurations.
    :type chains: List[FirewallChainConfig]
    """
    default_policy: FirewallPolicy
    chains: List[FirewallChainConfig]
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__firewall"
    id: str = ""
