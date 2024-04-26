from abc import ABC, abstractmethod
from netaddr import IPAddress, IPNetwork
from typing import NamedTuple, Optional, Tuple, Union
from cyst.api.environment.message import Message

from cyst.api.network.elements import Port, Interface, Connection


class Resolver(ABC):
    @abstractmethod
    def resolve_ip(self, id: str, port: int) -> IPAddress:
        pass


class Endpoint:
    def __init__(self, id: str, port: int, ip: Optional[IPAddress] = None):
        self._id = id
        self._port = port
        self._ip = ip

    @property
    def id(self) -> str:
        return self._id

    @property
    def port(self) -> int:
        return self._port

    @property
    def ip(self) -> IPAddress:
        return self._ip

    @ip.setter
    def ip(self, value: IPAddress) -> None:
        self._ip = value

    def __str__(self) -> str:
        return "Endpoint(ID: {}, Port: {}, IP: {})".format(self._id, self._port, self._ip)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: 'Endpoint') -> bool: #type: ignore
        return self.id == other.id and self.port == other.port and self.ip == other.ip


class Hop(NamedTuple):
    src: Endpoint
    dst: Endpoint

    # Necessary for reverse session to make sense
    def swap(self) -> 'Hop':
        return Hop(self.dst, self.src)


class ConnectionImpl(Connection):
    def __init__(self, hop: Optional[Hop] = None) -> None:
        self._hop = hop
        self._blocked = False
        self._delay = 0
        self._processing_time = 1  # Setting a processing time to a non-zero value

    @property
    def hop(self) -> Hop:
        return self._hop #MYPY: might return optional

    @hop.setter
    def hop(self, value: Hop) -> None:
        self._hop = value

    @property
    def blocked(self) -> bool:
        return self._blocked

    @property
    def delay(self) -> int:
        return self._delay

    def set_params(self, blocked: Optional[bool] = None, delay: Optional[int] = None) -> None:
        if blocked is not None:
            self._blocked = blocked
        if delay is not None:
            self._delay = delay

    def evaluate(self, message: Message) -> Tuple[int, Message]:
        if self.blocked:
            # TODO: return error message
            return -1, message

        return self._processing_time + self._delay, message

    def __str__(self) -> str:
        return f"Connection({self._hop}, Blocked: {self._blocked}, Delay: {self._delay})"

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def cast_from(o: Connection) -> 'ConnectionImpl':
        if isinstance(o, ConnectionImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Connection interface")


class PortImpl(Port):
    def __init__(self, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0, id: str = "") -> None:
        self._id: str = id
        self._ip: Optional[IPAddress] = None
        self._net: Optional[IPNetwork] = None
        self._index: int = index
        self._endpoint: Optional[Endpoint] = None
        self._connection: Optional[Connection] = None

        # Had to use more inelegant check, because IP 0.0.0.0 translates to false
        if ip is not None and ip != "":
            if type(ip) is str:
                self._ip = IPAddress(ip)
            else:
                self._ip = ip

        if mask:
            # Had to use more inelegant check, because IP 0.0.0.0 translates to false
            if ip is None or ip == "":
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
        return self._endpoint #MYPY: might return optional

    # There are no restrictions on connecting an endpoint to the port
    def connect_endpoint(self, endpoint: Endpoint, connection: Connection) -> None:
        self._endpoint = endpoint
        self._connection = connection

    @property
    def index(self) -> int:
        return self._index

    def set_index(self, value: int = 0) -> None:
        self._index = value

    @property
    def connection(self) -> Connection:
        return self._connection

    def set_connection(self, value: Connection) -> None:
        self._connection = value

    # Returns true if given ip belongs to the network
    def routes(self, ip: Union[str, IPAddress] = ""):
        ip = ip if isinstance(ip, IPAddress) else IPAddress(ip)
        return self._net and ip in self._net

    def id(self) -> str:
        return self._id

    @staticmethod
    def cast_from(o: Port) -> 'PortImpl':
        if isinstance(o, PortImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Port interface")


# Interface is just a port, which preserves gateway information (that is a port for end devices)
class InterfaceImpl(PortImpl, Interface):

    def __init__(self, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0, id: str = ""):
        super(InterfaceImpl, self).__init__(ip, mask, index, id)

        self._gateway_ip: Optional[IPAddress] = None

        if self._ip and self._net:
            # Gateway is by default first host in the network
            self._gateway_ip = next(self._net.iter_hosts())

    def set_ip(self, value: Union[str, IPAddress]) -> None:
        super(InterfaceImpl, self).set_ip(value)

        if self._ip and self._net:
            # Gateway is by default first host in the network
            self._gateway_ip = next(self._net.iter_hosts())

    def set_net(self, value: IPNetwork) -> None:
        super(InterfaceImpl, self).set_net(value)
        self._gateway_ip = next(self._net.iter_hosts())

    def set_mask(self, value: str) -> None:
        super(InterfaceImpl, self).set_mask(value)
        self._gateway_ip = next(self._net.iter_hosts())

    @property
    def gateway(self) -> Optional[IPAddress]:
        return self._gateway_ip

    @property
    def gateway_id(self) -> Optional[str]:
        return self._endpoint.id #MYPY: endpoint might be None

    def connect_gateway(self, ip: IPAddress, connection: Connection, id: str, port: int = 0) -> None:
        if not self._gateway_ip:
            raise Exception("Trying to connect a gateway to an interface without first specifying network parameters")

        if self._gateway_ip != ip:
            raise Exception("Connecting a gateway with wrong configuration")

        self.connect_endpoint(Endpoint(id, port, ip), connection)

    @staticmethod
    def cast_from(o: Interface) -> 'InterfaceImpl':
        if isinstance(o, InterfaceImpl):  #MYPY: Incorrect type in this method and in parent class
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Interface interface")
