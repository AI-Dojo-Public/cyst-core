from typing import List, Optional, Tuple, Union
from netaddr import IPAddress

from environment.access import Authorization, AccessLevel
from environment.message import MessageType
from environment.network_elements import Interface


# TODO The role of data and tokens is still unfinished bussiness - currently there is impossible to receive partial tokens (e.g. username only)
class Data:
    def __init__(self, id, owner):
        self._id = id
        self._owner = owner

    def __str__(self):
        return "Data [id: {}, owner: {}]".format(self._id, self._owner)

    def __repr__(self):
        return self.__str__()


class Service:
    def __init__(self, id: str) -> None:
        self._id = id
        self._node = None
        self._public_data = []
        self._private_data = []
        self._public_authorizations = []
        self._private_authorizations = []
        self._tags = set()
        self._enable_session = False
        self._session_access_level = AccessLevel.NONE

    @property
    def id(self) -> str:
        return self._id

    @property
    def tags(self):
        return self._tags

    def set_node(self, id):
        self._node = id

    def add_private_data(self, data):
        self._private_data.append(data)

    def add_public_data(self, data):
        self._public_data.append(data)

    def add_private_authorization(self, *authorization: Authorization) -> None:
        for auth in authorization:
            self._private_authorizations.append(auth)

    def add_public_authorization(self, *authorization: Authorization) -> None:
        for auth in authorization:
            self._public_authorizations.append(auth)

    def add_tag(self, tag):
        self._tags.add(tag)

    def add_tags(self, *tags):
        for tag in tags:
            self.add_tag(tag)

    @property
    def public_data(self):
        return self._public_data

    @property
    def public_authorizations(self) -> List[Authorization]:
        return self._public_authorizations

    @property
    def enable_session(self) -> bool:
        return self._enable_session

    def set_enable_session(self, value: bool) -> None:
        self._enable_session = value

    @property
    def session_access_level(self) -> AccessLevel:
        return self._session_access_level

    def set_session_access_level(self, value) -> None:
        self._session_access_level = value


class Node:
    def __init__(self, id: str, type: str = "Node", ip: Union[str, IPAddress] = "", mask: str = ""):
        self._id = id
        self._type = type
        self._interfaces = []
        self._ip = None
        if ip:
            self._interfaces.append(Interface(ip, mask))

    @property
    def id(self) -> str:
        return self._id

    @property
    def type(self) -> str:
        return self._type

    @property
    def ips(self) -> List[IPAddress]:
        return [x.ip for x in self._interfaces]

    @property
    def interfaces(self) -> List[Interface]:
        return self._interfaces

    def add_interface(self, i: Interface) -> int:
        # TODO Currently there is no control of interface overlaps. Question is whether it matters...
        self._interfaces.append(i)
        index = len(self._interfaces) - 1
        i.set_index(index)
        return index

    # Gateway returns both the IP address of the gateway and the port index
    def gateway(self, ip: Union[str, IPAddress] = "") -> Optional[Tuple[IPAddress, int]]:
        # If no IP is specified the the first gateway is used as a default gateway
        if not self._interfaces:
            return None

        # Explicit query for default gateway
        if not ip:
            return self._interfaces[0].gateway_ip, 0

        # Checking all available routes for exact one
        for iface in self._interfaces:
            if iface.routes(ip):
                return iface.gateway_ip, iface.index

        # Using a default one
        return self._interfaces[0].gateway_ip, 0

    def process_message(self, message) -> int:
        if message.type == MessageType.ACK:
            return 0

        print("Processing message at node {}. {}".format(self.id, message))
        return 0


class PassiveNode(Node):
    def __init__(self, id: str, ip: str = "", mask: str = "") -> None:
        self._data = []
        self._tokens = []
        self._services = {}
        super(PassiveNode, self).__init__(id, type="Passive node", ip=ip, mask=mask)

    def add_data(self, data):
        self._data.append(data)

    def add_token(self, token):
        self._tokens.append(token)

    def add_service(self, service):
        self._services[service.id] = service
        service.set_node(self._id)

    @property
    def services(self):
        return self._services
