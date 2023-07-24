from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from netaddr import IPAddress, IPNetwork


class FirewallPolicy(Enum):
    """
    Represents a firewall policy, which dictates how network traffic is handled.

    Possible values:
        :ALLOW: The traffic is allowed to pass.
        :DENY: The traffic is dropped.
    """
    ALLOW = 0,
    DENY = 1


@dataclass
class FirewallRule:
    """
    Represents a firewall rule, which applies a firewall policy based on source and destination.

    :param src_net: A source network of a traffic.
    :type src_net: IPNetwork

    :param dst_net: A destination network of a traffic.
    :type dst_net: IPNetwork

    :param service: A name of the destination service.
    :type service: str

    :param policy: A policy that should be applied.
    :type policy: FirewallPolicy
    """
    src_net: IPNetwork
    dst_net: IPNetwork
    service: str
    policy: FirewallPolicy


class FirewallChainType(Enum):
    """
    A firewall chain represents a set of rules that are applied to a network traffic. The type depends on the direction
    of the traffic.

    Possible values:
        :INPUT: The traffic originates at the same node as the firewall.
        :OUTPUT: The traffic is destined to the same node as the firewall.
        :FORWARD: The traffic is passing through the same node as the firewall.
    """
    INPUT = 0,
    OUTPUT = 1,
    FORWARD = 2


class Firewall(ABC):
    """
    Firewall is represented as a collection of chains, with a default policy that is applied, unless specified
    otherwise.
    """
    @abstractmethod
    def list_rules(self, chain: Optional[FirewallChainType] = None) -> List[Tuple[FirewallChainType, FirewallPolicy,
                                                                                  List[FirewallRule]]]:
        """
        List rules registered in the firewall.

        :param chain: If specified, lists only rules associated with the given chain.
        :type chain: Optional[FirewallChainType]

        :return: A collection of rules with associated chain and the default policy.
        """

    @abstractmethod
    def add_local_ip(self, ip: IPAddress) -> None:
        """
        Add an IP address that is considered local for the purpose of determining the chain of processed traffic.

        :param ip: The IP address to add.
        :type ip: IPAddress
        """

    @abstractmethod
    def remove_local_ip(self, ip: IPAddress) -> None:
        """
        Remove an IP address that is considered local for the purpose of determining the chain of processed traffic.

        :param ip: The IP address to remove.
        :type ip: IPAddress
        """

    @abstractmethod
    def add_rule(self, chain: FirewallChainType, rule: FirewallRule) -> None:
        """
        Adds a rule to a given chain.

        :param chain: The chain to apply the rule to.
        :type chain: FirewallChainType

        :param rule: The rule to add.
        :type rule: FirewallRule
        """

    @abstractmethod
    def remove_rule(self, chain: FirewallChainType, index: int) -> None:
        """
        Removes a rule from a given chain.

        :param chain: The chain to remove the rule from.
        :type chain: FirewallChainType

        :param index: An index of the rule within the chain.
        :type index: int
        """

    @abstractmethod
    def set_default_policy(self, chain: FirewallChainType, policy: FirewallPolicy) -> None:
        """
        Sets a default policy for a given chain.

        :param chain: The chain to set default policy at.
        :type chain: FirewallChainType

        :param policy: The default policy to set.
        :type policy: FirewallPolicy
        """

    @abstractmethod
    def get_default_policy(self, chain: FirewallChainType) -> FirewallPolicy:
        """
        Gets the default policy for a given chain.

        :param chain: The chain to get the policy from.
        :type chain: FirewallChainType

        :return: The default policy.
        """

    @abstractmethod
    def evaluate(self, src_ip: IPAddress, dst_ip: IPAddress, dst_service: str) -> Tuple[bool, int]:
        """
        Evaluates, whether a traffic with given source and destination will pass through or not, according to the rules.

        :param src_ip: The source IP of the traffic.
        :type src_ip: IPAddress

        :param dst_ip: The destination IP of the traffic.
        :type dst_ip: IPAddress

        :param dst_service: The destination service of the traffic.
        :type dst_service: str

        :return: A tuple indicating if the traffic should pass and how long the processing took.
        """
