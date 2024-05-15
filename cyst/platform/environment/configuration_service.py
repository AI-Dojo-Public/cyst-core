from __future__ import annotations

import uuid

from typing import TYPE_CHECKING, List, Optional, Any, Type, Dict

from cyst.api.environment.configuration import ServiceConfiguration, ServiceParameter, ActiveServiceInterfaceType
from cyst.api.host.service import PassiveService, Service, ActiveService
from cyst.api.logic.access import AccessScheme, AuthenticationProvider, Authorization, AccessLevel
from cyst.api.logic.data import Data
from cyst.api.network.node import Node
from cyst.api.network.session import Session

from cyst.platform.host.service import PassiveServiceImpl, ServiceImpl
from cyst.platform.logic.data import DataImpl
from cyst.platform.network.node import NodeImpl

if TYPE_CHECKING:
    from cyst.platform.main import CYSTPlatform


class ServiceConfigurationImpl(ServiceConfiguration):
    def __init__(self, platform: CYSTPlatform):
        self._platform = platform

    def create_active_service(self, type: str, owner: str, name: str, node: Node,
                              service_access_level: AccessLevel = AccessLevel.LIMITED,
                              configuration: Optional[Dict[str, Any]] = None, id: str = "") -> Optional[Service]:
        return _create_active_service(self._platform, type, owner, name, node, service_access_level, configuration, id)

    def get_service_interface(self, service: ActiveService,
                              interface_type: Type[ActiveServiceInterfaceType]) -> ActiveServiceInterfaceType:
        if isinstance(service, interface_type):
            return service
        else:
            raise RuntimeError("Given active service does not provide control interface of given type.")

    def create_passive_service(self, type: str, owner: str, version: str = "0.0.0", local: bool = False,
                               service_access_level: AccessLevel = AccessLevel.LIMITED, id: str = "") -> Service:
        return _create_passive_service(self._platform, type, owner, version, local, service_access_level, id)

    def update_service_version(self, service: PassiveService, version: str = "0.0.0") -> None:
        service = PassiveServiceImpl.cast_from(service)
        service.version = version

    def set_service_parameter(self, service: PassiveService, parameter: ServiceParameter, value: Any) -> None:
        service = PassiveServiceImpl.cast_from(service)
        if parameter == ServiceParameter.ENABLE_SESSION:
            service.set_enable_session(value)
        elif parameter == ServiceParameter.SESSION_ACCESS_LEVEL:
            service.set_session_access_level(value)

    def create_data(self, id: Optional[str], owner: str, description: str) -> Data:
        return _create_data(self._platform, id, owner, description)

    def public_data(self, service: PassiveService) -> List[Data]:
        return PassiveServiceImpl.cast_from(service).public_data

    def private_data(self, service: PassiveService) -> List[Data]:
        return PassiveServiceImpl.cast_from(service).private_data

    def public_authorizations(self, service: PassiveService) -> List[Authorization]:
        return PassiveServiceImpl.cast_from(service).public_authorizations

    def private_authorizations(self, service: PassiveService) -> List[Authorization]:
        return PassiveServiceImpl.cast_from(service).private_authorizations

    def sessions(self, service: PassiveService) -> List[Session]:
        return PassiveServiceImpl.cast_from(service).sessions

    def provides_auth(self, service: PassiveService, auth_provider: AuthenticationProvider) -> None:
        return PassiveServiceImpl.cast_from(service).add_provider(auth_provider)

    def set_scheme(self, service: PassiveService, scheme: AccessScheme) -> None:
        return PassiveServiceImpl.cast_from(service).add_access_scheme(scheme)


# ------------------------------------------------------------------------------------------------------------------
# ServiceConfiguration (with trampoline)
def _create_active_service(self: CYSTPlatform, type: str, owner: str, name: str, node: Node,
                          service_access_level: AccessLevel = AccessLevel.LIMITED,
                          configuration: Optional[Dict[str, Any]] = None, id: str = "") -> Optional[Service]:
    if not id:
        id = NodeImpl.cast_from(node).id + "." + name

    srv = self._infrastructure.service_store.create_active_service(type, owner, name, node, service_access_level, configuration, id)
    s = ServiceImpl(type, srv, name, owner, service_access_level, id)
    if s:
        self._general_configuration.add_object(id, s)

    return s


def _create_passive_service(self: CYSTPlatform, type: str, owner: str, version: str = "0.0.0", local: bool = False,
                           service_access_level: AccessLevel = AccessLevel.LIMITED, id: str = "") -> Service:
    if not id:
        id = str(uuid.uuid4())

    p = PassiveServiceImpl(type, owner, version, local, service_access_level, id)
    self._general_configuration.add_object(id, p)
    return p


def _create_data(self: CYSTPlatform, id: Optional[str], owner: str, description: str) -> Data:
    if not id:
        id = str(uuid.uuid4())
    d = DataImpl(id, owner, description)
    self._general_configuration.add_object(id, d)
    return d
