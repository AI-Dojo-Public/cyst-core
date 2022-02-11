from abc import ABC, abstractmethod
from typing import List, Union, Optional, Tuple, Dict
from netaddr import IPAddress

from cyst.api.host.service import Service
from cyst.api.network.elements import Interface


class Node(ABC):
    """
    A network node is a main building block of simulation topology. It is modelled as a collection of services and a
    set of network interfaces.
    """

    @property
    @abstractmethod
    def type(self) -> str:
        """
        Returns the type of the node. Currently, only two types are supported - "node" and "router".

        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def services(self) -> Dict[str, Service]:
        """
        Returns a collection of service instances, which are present at the node.

        :rtype: Dict[str, Service]
        """
        pass

    @property
    @abstractmethod
    def shell(self) -> Optional[Service]:
        """
        Returns a designated shell service (if there is one).

        :rtype: Optional[Service]
        """
        pass

    @property
    @abstractmethod
    def interfaces(self) -> List[Interface]:
        """
        Returns network interfaces of the node.

        :rtype: List[Interface]
        """
        pass

    @property
    @abstractmethod
    def ips(self) -> List[IPAddress]:
        """
        Returns a list of IP addresses, which are set across all interfaces of the node.

        :rtype: List[IPAddress]
        """
        pass

    @abstractmethod
    def gateway(self, ip: Union[str, IPAddress] = "") -> Optional[Tuple[IPAddress, int]]:
        """
        Calculates, which gateway would be used by the node, if a message was sent to a given destination IP address.
        The gateway is selected according to the routing rules.

        :param ip: The destination IP address.
        :type ip: Union[str, IPAddress]

        :return: A gateway IP address together with port index (if one is found).
        :rtype: Optional[Tuple[IPAddress, int]]
        """
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass
