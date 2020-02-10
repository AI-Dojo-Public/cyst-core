# This file is a preliminary effort for hiding implementation details and sensitive information from active actors.
# E.g., a session currently contains a full path with user ids in it, however, these should only be accessible to
# the environment.
# In this iteration, everything will be grouped under the environment.views namespace, but in the end, it should
# probably end as top level api for users with easiest names possible and viewed classes should be changed to private

import uuid

from netaddr import IPAddress
from dataclasses import dataclass
from typing import Optional, List, Dict, Set

from environment.access import AccessLevel, Authorization


@dataclass(frozen=True)
class PortView:
    ip: Optional[IPAddress]
    mask: Optional[str]


@dataclass(frozen=True)
class InterfaceView:
    ip: Optional[IPAddress]
    mask: Optional[str]
    gw: Optional[IPAddress]


# TODO: Session currently does not store info about IPs and should probably in the future store a whole IP path.
@dataclass(frozen=True)
class SessionView:
    id: uuid
    source: IPAddress
    destination: IPAddress


# TODO there is a big gaping hole that needs to be plugged. Until then, the ServiceView basically returns the same as
# information discovery
class ServiceView:
    def __init__(self, id: str, service_access_level: AccessLevel):
        self._id = id
        self._service_access_level = service_access_level
        # This is by default until there is a reason to define ActiveServiceView
        self._type = "active"

    @property
    def id(self) -> str:
        return self._id

    @property
    def service_access_level(self) -> AccessLevel:
        return self._service_access_level

    def __str__(self) -> str:
        return "Service [ID: " + self._id + ", Service access level: " + str(self._service_access_level) + "]"

    def __repr__(self) -> str:
        return self.__str__()


class PassiveServiceView(ServiceView):
    def __init__(self, id: str, tags: Set['Tag'], public_data: List['Data'], public_authorizations: List[Authorization],
                 enable_session: bool, session_access_level: AccessLevel, service_access_level: AccessLevel):

        super(PassiveServiceView, self).__init__(id, service_access_level)

        self._type = "passive"
        self._tags = tags
        self._public_data = public_data
        self._public_authorizations = public_authorizations
        self._enable_session = enable_session
        self._session_access_level = session_access_level
        self._service_access_level = service_access_level

    @property
    def tags(self) -> Set['Tag']:
        return self._tags

    @property
    def public_data(self) -> List['Data']:
        return self._public_data

    @property
    def public_authorizations(self) -> List[Authorization]:
        return self._public_authorizations

    @property
    def enable_session(self) -> bool:
        return self._enable_session

    @property
    def session_access_level(self) -> AccessLevel:
        return self._session_access_level

    def __str__(self) -> str:
        return "Service [ID: " + self._id + ", tags: " + str(self._tags) + ", public data: " + str(self._public_data) + \
               ", public authorizations: " + str(self._public_authorizations) + ", enables session: " + \
               str(self._enable_session) + ", session access level: " + str(self._session_access_level) + \
               ", Service access level: " + str(self._service_access_level) + "]"

    def __repr__(self) -> str:
        return self.__str__()


class NodeView:
    def __init__(self):
        self._interfaces = []
        self._services = {}

    def add_interface(self, interface: InterfaceView) -> None:
        self._interfaces.append(interface)

    @property
    def interfaces(self) -> List[InterfaceView]:
        return self._interfaces

    def add_service(self, service: ServiceView) -> None:
        self._services[service.id] = service

    @property
    def services(self) -> Dict[str, ServiceView]:
        return self._services

    def __repr__(self) -> str:
        return "[Interfaces: {}, Services: {}]".format(self._interfaces, self._services)
