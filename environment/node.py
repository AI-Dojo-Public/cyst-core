import ipaddress

from typing import List

from environment.message import MessageType
from environment.access import Authorization


#TODO The role of data and tokens is still unfinished bussiness - currently there is impossible to receive partial tokens (e.g. username only)
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


class Node:
    def __init__(self, id: str, type: str = "Node", ip: str = "", mask: str = ""):
        self._id = id
        self._type = type
        self._ip = None
        if ip:
            self._ip = ipaddress.ip_address(ip)

        self._net = None
        if mask:
            self._net = ipaddress.ip_network(ip + "/" + mask, strict=False)

    @property
    def id(self) -> str:
        return self._id

    @property
    def type(self) -> str:
        return self._type

    @property
    def ip(self) -> str:
        if not self._ip:
            return ""
        else:
            return str(self._ip)

    def set_ip(self, ip: str) -> None:
        self._ip = ipaddress.ip_address(ip)

    @property
    def mask(self) -> str:
        if not self._net:
            return ""
        else:
            return str(self._net.netmask)

    def set_mask(self, mask: str) -> None:
        self._net = ipaddress.ip_network((self._ip, mask), strict=False)

    @property
    def gateway(self) -> str:
        return str(next(self._net.hosts()))

    def process_message(self, message) -> int:
        if message.type == MessageType.ACK:
            return 0

        print("Processing message at node {}. {}".format(self.id, message))
        return 0


class PassiveNode(Node):
    def __init__(self, id):
        self._data = []
        self._tokens = []
        self._services = {}
        super(PassiveNode, self).__init__(id)
        self._type = "Passive node"

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
