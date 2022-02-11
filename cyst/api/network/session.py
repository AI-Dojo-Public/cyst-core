from abc import abstractmethod, ABC
from netaddr import IPAddress
from typing import List, Optional, Tuple


class Session(ABC):
    """
    A session represents a virtual connection between two nodes in the infrastructure. The session ignores the routing
    limitations imposed by router configuration.
    """
    @property
    @abstractmethod
    def owner(self) -> str:
        """
        Returns the owner of the session. This method is being slowly phased away.

        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """
        Returns a unique identifier of the session.

        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def parent(self) -> Optional['Session']:
        """
        Returns the parent session of this session (if there is one). Sessions can be chained together and a message
        traverses this chain sequentially.

        :rtype: Optional[Session]
        """
        pass

    @property
    @abstractmethod
    def path(self) -> List[Tuple[Optional[IPAddress], Optional[IPAddress]]]:
        """
        Returns a path trough the infrastructure, on which the session lies. The path is modelled as a set of "hops",
        i.e., tuples of IP addresses representing a source and destination of one connection. Note that a destination
        of preceding hop does not have to be the same as the source of the next hop. These can often differ, especially
        when a session is crossing between different networks.

        :rtype: List[Tuple[Optional[IPAddress], Optional[IPAddress]]]
        """
        pass

    @property
    @abstractmethod
    def end(self) -> Tuple[IPAddress, str]:
        """
        Returns the ultimate destination of the session. The result includes both the IP address of the node, and the
        service the session is linked to.

        :rtype: Tuple[IPAddress, str]
        """
        pass

    @property
    @abstractmethod
    def start(self) -> Tuple[IPAddress, str]:
        """
        Returns the start of the session. If the session has a parent, then a start of the parent is returned.
        The result includes both the IP address of the node, and the service the session is linked to.

        :rtype: Tuple[IPAddress, str]
        """
        pass
