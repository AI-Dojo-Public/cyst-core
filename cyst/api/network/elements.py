import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Tuple
from netaddr import IPNetwork, IPAddress
from uuid import uuid4

from cyst.api.environment.message import Message


@dataclass
class Route:
    """
    A route specifies which port should the traffic to specific network be routed through. Many routes can be specified
    for a node. If there is an overlap in network specification, than the resulting port is selected according to the
    route metrics (i.e., the lower the metric the higher the chance to be selected as the route). In case of a metric
    equality, the most specific network is selected.

    :param net: A network this route is related to.
    :type net: IPNetwork

    :param port: A port/interface index, where to route traffic to the particular network.
    :type port: int

    :param metric: A route metric used for deciding which route to use in case of network overlap.
    :type metric: int

    :param id: A unique identifier of the route. You very likely don't need to set it and just let it autogenerate.
    :type id: str
    """
    net: IPNetwork
    port: int
    metric: int = 100
    id: str = field(default_factory=lambda: str(uuid4()))

    # Custom comparison to enable sorting in a priority queue
    def __lt__(self, other: 'Route') -> bool:
        # Metric is a way to override the default longest-prefix routing
        if self.metric != other.metric:
            return self.metric < other.metric

        # This should usually suffice
        if self.net.prefixlen != other.net.prefixlen:
            # The comparison is inversed, because we want the longest prefix to have the lowest value and highest priority
            return self.net.prefixlen > other.net.prefixlen

        # This is just a fallback to have some stability in it
        return self.net.ip < other.net.ip


class Port(ABC):
    """
    A network port represents an abstraction of an ethernet port, with a given IP address and a given network. A network
    port does not support a default routing through a gateway and so it is used mostly for routers, which maintain
    their own routing tables based on the port indexes.
    """

    @property
    @abstractmethod
    def ip(self) -> Optional[IPAddress]:
        """
        Returns the IP address of the port.

        :rtype: Optional[IPAddress]
        """

    @property
    @abstractmethod
    def mask(self) -> Optional[str]:
        """
        Returns the network mask of the port.

        :rtype: Optional[str]
        """

    @property
    @abstractmethod
    def net(self) -> Optional[IPNetwork]:
        """
        Returns the network of the port.

        :rtype: Optional[IPNetwork]
        """

    @property
    @abstractmethod
    def connection(self) -> Optional['Connection']:
        """
        Returns the connection of the port.
        """


class Interface(Port, ABC):
    """
    A network interface represents an abstraction of an ethernet port, with a given IP address and a given network.
    The network interface automatically calculates the gateway and therefore enables a seamless networking.
    """

    @property
    @abstractmethod
    def gateway(self) -> Optional[IPAddress]:
        """
        Returns the IP address of the gateway.

        :rtype: Optional[IPAddress]
        """


class Connection(ABC):
    """
    Represents a connection between two network ports/interfaces. Connection supports setting of
    connection properties, such as delay or packet drops.
    """

    @property
    @abstractmethod
    def delay(self) -> int:
        """
        Returns the delay of the connection in simulated time units.

        :rtype: int
        """

    @property
    @abstractmethod
    def blocked(self) -> bool:
        """
        Returns whether the connection is blocked or not.

        :rtype: bool
        """

    @abstractmethod
    def set_params(self, delay: Optional[int] = None, blocked: Optional[bool] = None) -> None:
        """
        Sets the connection parameters, such as delay and blocked.

        :param delay: The delay of the connection in simulated time units.
        :type delay: int

        :param blocked: Whether the connection is blocked or not.
        :type blocked: bool
        """

    @abstractmethod
    def evaluate(self, message: Message) -> Tuple[int, Message]:
        """
        Evaluates the message based on the connection properties. The properties are checked in this order:

        1. The message is dropped: new response is formed from the message and delay is set to -1
        2. The message is delayed: the original message is returned alongside connections's delay
        3. The message is passed through: the original message is returned alongside 0 delay

        :param message: A message to evaluate.
        :type message: Message

        :return: A tuple of delay and message.
        """
