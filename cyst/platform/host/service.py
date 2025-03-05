from semver import VersionInfo
from typing import List, Set, Union, Tuple, Optional

import cyst
from cyst.api.host.service import Service, ActiveService, PassiveService, ServiceState
from cyst.api.logic.access import AccessLevel, AuthenticationToken, Authorization, AuthenticationProvider, AccessScheme
from cyst.api.logic.data import Data
from cyst.api.network.node import Node
from cyst.api.network.session import Session

from cyst.platform.logic.access import AuthorizationImpl
from cyst.platform.logic.data import DataImpl


class ServiceImpl(Service):

    def __init__(self, type: str, service: Union[ActiveService, PassiveService],
                 name: str, owner: str, service_access_level: AccessLevel = AccessLevel.LIMITED, id: str = ""):
        self._type = type
        self._service = service
        self._name = name
        self._owner = owner
        self._sal = service_access_level
        self._node = None
        self._sessions = []
        self._id = id

    @property
    def id(self) -> str:
        return self._id

    @property
    def type(self) -> str:
        return self._type

    def set_node(self, id):
        self._node = id

    @property
    def name(self) -> str:
        return self._name

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def service_access_level(self) -> AccessLevel:
        return self._sal

    @property
    def passive(self) -> bool:
        return isinstance(self._service, PassiveService)

    @property
    def sessions(self) -> List[Session]:
        return self._sessions

    @sessions.setter
    def sessions(self, value: List) -> None:
        self._sessions = value

    def add_session(self, session: Session) -> None:
        if session not in self._sessions:
            self._sessions.append(session)

    @property
    def passive_service(self) -> Optional[PassiveService]:
        if isinstance(self._service, PassiveService):
            return self._service
        return None

    @property
    def active_service(self) -> Optional[ActiveService]:
        if isinstance(self._service, ActiveService):
            return self._service
        return None

    @staticmethod
    def cast_from(o: Service) -> 'ServiceImpl':
        if isinstance(o, ServiceImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Service interface")


class PassiveServiceImpl(ServiceImpl, PassiveService):
    def __init__(self, type: str, owner: str, version: str = "0.0.0", local: bool = False,
                 service_access_level: AccessLevel = AccessLevel.LIMITED, id: str = "") -> None:
        super(PassiveServiceImpl, self).__init__(type, self, type, owner, service_access_level, id)

        self._state = ServiceState.INIT
        self._version = VersionInfo.parse(version)
        self._public_data: List[Data] = []
        self._private_data: List[Data] = []
        self._public_authorizations: List[Authorization] = []
        self._private_authorizations: List[Authorization] = []
        self._tags: Set[str] = set()  # Mypy: I did not find out the type
        self._enable_session = False
        self._session_access_level = AccessLevel.NONE
        self._local = local
        self._provided_auths: List[AuthenticationProvider] = []
        self._access_schemes: List[AccessScheme] = []
        self._active_authorizations: List[Authorization] = []
        self._authentication_tokens = set()

    # ------------------------------------------------------------------------------------------------------------------
    # PassiveService
    @property
    def version(self) -> VersionInfo:
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        self._version = VersionInfo.parse(value)

    @property
    def state(self) -> ServiceState:
        return self._state

    def set_state(self, value: ServiceState) -> None:
        self._state = value

    @property
    def tags(self):
        return self._tags

    @property
    def local(self) -> bool:
        return self._local

    # ------------------------------------------------------------------------------------------------------------------

    def add_public_data(self, data: DataImpl):
        self._public_data.append(data)

    def add_private_data(self, data: DataImpl):
        self._private_data.append(data)

    def add_public_authorization(self, *authorization: Authorization) -> None:
        for auth in authorization:
            self._public_authorizations.append(auth)

    def add_private_authorization(self, *authorization: Authorization) -> None:
        for auth in authorization:
            self._private_authorizations.append(auth)

    def add_tags(self, *tags):
        for tag in tags:
            self._tags.add(tag)

    def add_provider(self, provider: AuthenticationProvider):
        self._provided_auths.append(provider)
        if isinstance(provider, cyst.platform.logic.access.AuthenticationProviderImpl):
            provider.set_service(self._id)

    def add_access_scheme(self, scheme: AccessScheme):
        self._access_schemes.append(scheme)

    def add_active_authorization(self, auth: Authorization):
        self._active_authorizations.append(auth)

    def add_authentication_token(self, token: AuthenticationToken):
        self._authentication_tokens.add(token)

    def assess_authorization(self, auth: Authorization, access_level: AccessLevel, node: str,
                             service: str) -> Tuple[bool, str]:
        auth = AuthorizationImpl.cast_from(auth)

        # workaround for federated authorization
        if auth.services == ["*"] and (auth.nodes == ["*"] or node in auth.nodes):
            return True, "Federated authorization is valid"

        for active_auth in map(AuthorizationImpl.cast_from, self._active_authorizations):
            if auth.matching_id(active_auth) and access_level <= active_auth.access_level and \
                    node in active_auth.nodes and service in active_auth.services:
                return True, "Authorization is valid."
        return False, "Invalid authorization."

    @property
    def private_data(self) -> List[Data]:
        return self._private_data

    @property
    def public_data(self) -> List[Data]:
        return self._public_data

    @property
    def private_authorizations(self) -> List[Authorization]:
        return self._private_authorizations

    @property
    def public_authorizations(self) -> List[Authorization]:
        return self._public_authorizations

    @property
    def authentication_tokens(self) -> Set[AuthenticationToken]:
        return self._authentication_tokens

    @property
    def enable_session(self) -> bool:
        return self._enable_session

    @property
    def access_schemes(self) -> List[AccessScheme]:
        return self._access_schemes

    def set_enable_session(self, value: bool) -> None:
        self._enable_session = value

    @property
    def session_access_level(self) -> AccessLevel:
        return self._session_access_level

    def set_session_access_level(self, value) -> None:
        self._session_access_level = value

    @staticmethod
    def cast_from(o: PassiveService) -> 'PassiveServiceImpl':
        if isinstance(o, PassiveServiceImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the PassiveService interface")
