import uuid

from collections import Iterable
from netaddr import *
from typing import NamedTuple, Optional, List, Union


from environment.views import PortView, InterfaceView


class Endpoint(NamedTuple):
    id: str
    port: int


class Hop(NamedTuple):
    src: Endpoint
    dst: Endpoint

    # Necessary for reverse session to make sense
    def swap(self) -> 'Hop':
        return Hop(self.dst, self.src)


class Route(NamedTuple):
    net: IPNetwork
    port: int


# This class is here as a future proofing
class Connection:
    def __init__(self):
        pass


class Port:
    def __init__(self, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0) -> None:
        self._ip = None
        self._net = None
        self._index = index
        self._endpoint = None

        if ip:
            if type(ip) is str:
                self._ip = IPAddress(ip)
            else:
                self._ip = ip

        if mask:
            if not ip:
                raise Exception("Netmask cannot be specified without an IP address")
            if type(ip) is str:
                self._net = IPNetwork(ip + "/" + mask)
            else:
                self._net = IPNetwork(str(ip) + "/" + mask)

    @property
    def ip(self) -> Optional[IPAddress]:
        return self._ip

    def set_ip(self, value: Union[str, IPAddress]) -> None:
        if type(value) is str:
            self._ip = IPAddress(value)
        else:
            self._ip = value

        if self._net:
            # This str dance is sadly necessary, because IPNetwork does not enable changing of IP address
            if type(value) is str:
                self._net = IPNetwork(value + "/" + str(self._net.netmask))
            else:
                self._net = IPNetwork(str(value) + "/" + str(self._net.netmask))

    # Only IP address is returned as an object. Mask is for informative purposes outside construction, so it is
    # returned as a string
    @property
    def mask(self) -> Optional[str]:
        if self._net:
            return str(self._net.netmask)
        else:
            return None

    def set_mask(self, value: str) -> None:
        if not self._ip:
            raise Exception("Netmask cannot be specified without an IP address")

        # This str dance is necessary, because netaddr does not acknowledge changing IPNetwork IP address
        self._net = IPNetwork(str(self._ip) + "/" + value)

    @property
    def net(self) -> Optional[IPNetwork]:
        return self._net

    def set_net(self, value: IPNetwork) -> None:
        self._net = value

    @property
    def endpoint(self) -> Endpoint:
        return self._endpoint

    # There are no restrictions on connecting an endpoint to the port
    def connect_endpoint(self, endpoint: Endpoint) -> None:
        self._endpoint = endpoint

    @property
    def index(self) -> int:
        return self._index

    def set_index(self, value: int = 0) -> None:
        self._index = value

    # Returns true if given ip belongs to the network
    def routes(self, ip: Union[str, IPAddress] = ""):
        if ip in self._net:
            return True
        else:
            return False

    def view(self) -> PortView:
        return PortView(self._ip, self.mask)


# Interface is just a port, which preserves gateway information (that is a port for end devices)
class Interface(Port):
    def __init__(self, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0):
        super(Interface, self).__init__(ip, mask, index)

        self._gateway_ip = None

        if self._ip and self._net:
            # Gateway is by default first host in the network
            self._gateway_ip = next(self._net.iter_hosts())

    def set_ip(self, value: Union[str, IPAddress]) -> None:
        super(Interface, self).set_ip(value)

        if self._ip and self._net:
            # Gateway is by default first host in the network
            self._gateway_ip = next(self._net.iter_hosts())

    def set_net(self, value: IPNetwork) -> None:
        super(Interface, self).set_net(value)
        self._gateway_ip = next(self._net.iter_hosts())

    def set_mask(self, value: str) -> None:
        super(Interface, self).set_mask(value)
        self._gateway_ip = next(self._net.iter_hosts())

    @property
    def gateway_ip(self) -> Optional[IPAddress]:
        return self._gateway_ip

    @property
    def gateway_id(self) -> Optional[str]:
        return self._endpoint.id

    def connect_gateway(self, ip: IPAddress, id: str, port: int = 0) -> None:
        if not self._gateway_ip:
            raise Exception("Trying to connect a gateway to an interface without first specifying network parameters")

        if self._gateway_ip != ip:
            raise Exception("Connecting a gateway with wrong configuration")

        self._endpoint = Endpoint(id, port)

    def view(self) -> InterfaceView:
        return InterfaceView(self._ip, self.mask, self._gateway_ip)


# The session represents an existing chain of connections, which can be traversed without authorization by its owner
class Session:
    def __init__(self, owner: str, parent: 'Session' = None, path: List[Hop] = None) -> None:
        self._id = uuid.uuid4()
        if not owner:
            raise Exception("Cannot create a session without an owner")

        self._owner = owner
        self._parent = parent

        if self._parent and parent.owner != self._owner:
            raise Exception("Cannot link sessions with different owners")

        if not path:
            raise Exception("Cannot create a session without a path")

        self._path = path

        if self._parent and self._parent.endpoint == self._path[-1].dst:
            raise Exception("Cannot create a session sharing an endpoint with a parent")

    class ForwardIterator(Iterable):
        def __init__(self, session: 'Session') -> None:
            self._session = session
            self._path_index = 0
            if session.parent:
                self._parent_iterator = session.parent.get_forward_iterator()
            else:
                self._parent_iterator = None
            self._parent_traversed = False

        def has_next(self) -> bool:
            if self._parent_iterator and self._parent_iterator.has_next():
                return True

            if self._path_index != len(self._session.path):
                return True

            return False

        def __iter__(self):
            return self

        def __next__(self) -> Hop:
            if self._parent_traversed or not self._session.parent:
                if self._path_index != len(self._session.path):
                    result = self._session.path[self._path_index]
                    self._path_index += 1
                    return result
                else:
                    raise StopIteration
            else:
                if self._parent_iterator.has_next():
                    return self._parent_iterator.__next__()
                else:
                    self._parent_traversed = True
                    return self.__next__()

    class ReverseIterator(Iterable):
        def __init__(self, session: 'Session') -> None:
            self._session = session
            self._path_index = len(self._session.path) - 1
            if session.parent:
                self._parent_iterator = session.parent.get_reverse_iterator()
            else:
                self._parent_iterator = None
            self._parent_traversing = False

        def has_next(self) -> bool:
            if self._path_index >= 0:
                return True

            elif self._parent_iterator:
                return self._parent_iterator.has_next()

            return False

        def __iter__(self):
            return self

        def __next__(self) -> Hop:
            if self._path_index >= 0:
                result = self._session.path[self._path_index]
                self._path_index -= 1
                return result.swap()
            else:
                if not self._parent_traversing:
                    self._parent_traversing = True
                    return self.__next__()
                else:
                    if self._parent_iterator.has_next():
                        result = self._parent_iterator.__next__()
                        return result
                    else:
                        raise StopIteration

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def id(self) -> str:
        return str(self._id)

    @property
    def parent(self) -> 'Session':
        return self._parent

    @property
    def path(self) -> List[Hop]:
        return self._path

    def get_forward_iterator(self) -> ForwardIterator:
        return Session.ForwardIterator(self)

    def get_reverse_iterator(self) -> ReverseIterator:
        return Session.ReverseIterator(self)

    # Endpoint is a destination node of the last path hop
    @property
    def endpoint(self) -> Endpoint:
        return self._path[-1].dst

    def __str__(self) -> str:
        result = []
        for node in self.get_forward_iterator():
            result.append(node)
        return "[ID: {}, Owner: {}, Path: {}]".format(self.id, self.owner, result)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other) -> bool:
        if not other:
            return False

        return self.owner == other.owner and \
            self.parent == other.parent and \
            self.path == other.path
