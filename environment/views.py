# This file is a preliminary effort for hiding implementation details and sensitive information from active actors.
# E.g., a session currently contains a full path with user ids in it, however, these should only be accessible to
# the environment.
# In this iteration, everything will be grouped under the environment.views namespace, but in the end, it should
# probably end as top level api for users with easiest names possible and viewed classes should be changed to private

import uuid

from netaddr import IPAddress
from dataclasses import dataclass
from typing import Optional

from environment.access import AccessLevel


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
@dataclass(frozen=True)
class ServiceView:
    id: str
    tags: set
    public_data: []
    public_authorizations: []
    enable_session: bool
    session_access_level: AccessLevel
    service_access_level: AccessLevel


class NodeView:
    def __init__(self):
        self._interfaces = []
        self._services = []

    def add_interface(self, interface: InterfaceView) -> None:
        self._interfaces.append(interface)

    def add_service(self, service: ServiceView) -> None:
        self._services.append(service)

    def __repr__(self) -> str:
        return "[Interfaces: {}, Services: {}]".format(self._interfaces, self._services)
