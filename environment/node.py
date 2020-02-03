from typing import List, Optional, Tuple, Union
from netaddr import IPAddress
from semver import VersionInfo

from environment.access import Authorization, AccessLevel
from environment.message import MessageType
from environment.network_elements import Interface
from environment.views import NodeView, ServiceView, InterfaceView


# TODO Data handling is a next big thing - how to manage access to private data, how to express encrypted or hashed data
#                                          how to reasonably link data, tokens and services
class Data:
    def __init__(self, id, owner):
        self._id = id
        self._owner = owner

    def __str__(self):
        return "Data [id: {}, owner: {}]".format(self._id, self._owner)

    def __repr__(self):
        return self.__str__()


class Service:
    def __init__(self, id: str, version: str = "0.0.0") -> None:
        self._id = id
        self._version = VersionInfo.parse(version)
        self._node = None
        self._public_data = []
        self._private_data = []
        self._public_authorizations = []
        self._private_authorizations = []
        self._tags = set()
        self._enable_session = False
        self._session_access_level = AccessLevel.NONE
        self._service_access_level = AccessLevel.LIMITED

    @property
    def id(self) -> str:
        return self._id

    @property
    def version(self) -> VersionInfo:
        return self._version

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

    @property
    def service_access_level(self) -> AccessLevel:
        return self._service_access_level

    def set_service_access_level(self, value) -> None:
        self._service_access_level = value

    def view(self) -> ServiceView:
        return ServiceView(self._id, self._tags, self._public_data, self._public_authorizations, self._enable_session,
                           self._session_access_level, self._service_access_level)


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

    # Active nodes should implement their own view
    def view(self) -> NodeView:
        pass


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

    def view(self) -> NodeView:
        nv = NodeView()

        for iface in self._interfaces:
            nv.add_interface(InterfaceView(iface.ip, iface.mask, iface.gateway_ip))

        for service in self._services.values():
            nv.add_service(ServiceView(service.id, service.tags, service.public_data, service.public_authorizations,
                                       service.enable_session, service.session_access_level, service.service_access_level))

        return nv
