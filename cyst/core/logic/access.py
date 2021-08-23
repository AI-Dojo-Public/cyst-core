import sqlite3
import uuid

from enum import IntEnum
from itertools import product
from typing import List, Tuple, Union, Optional
from sqlite3 import Error

from netaddr import IPAddress

from cyst.api.configuration.logic.access import AccessLevel
from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.host.service import Service
from cyst.api.logic.access import Authorization, AuthenticationToken, AuthenticationTokenSecurity, \
    AuthenticationTokenType, AuthenticationProvider, AuthenticationTarget, AuthenticationProviderType, AccessScheme
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.logic.data import Data
from cyst.api.network.node import Node

from cyst.core.network.node import NodeImpl
from cyst.core.host.service import ServiceImpl, PassiveServiceImpl
from cyst.core.logic.data import DataImpl


class AuthorizationImpl(Authorization):
    def __init__(self, identity: str = "", nodes: List[str] = None, services: List[str] = None,
                 access_level: AccessLevel = AccessLevel.NONE, id: Optional[str] = None, token: Optional[str] = None):
        if services is None or not services:
            services = ["*"]
        if nodes is None or not nodes:
            nodes = ["*"]
        self._id = id
        self._identity = identity
        self._nodes = nodes
        self._services = services
        self._access_level = access_level
        self._token = token
        self._expiration = -1  # TODO

    def __eq__(self, other: 'Authorization') -> bool:
        if not other:
            return False

        other = AuthorizationImpl.cast_from(other)
        return self.id == other.id or (
                self.identity == other.identity and
                self.nodes == other.nodes and
                self.services == other.services and
                self.access_level == other.access_level and
                self.token == other.token
        )

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, value: str) -> None:
        self._id = value

    @property
    def identity(self) -> str:
        return self._identity

    @identity.setter
    def identity(self, value: str) -> None:
        self._identity = value

    @property
    def nodes(self) -> List[str]:
        return self._nodes

    @nodes.setter
    def nodes(self, value: List[str]) -> None:
        self._nodes = value

    @property
    def services(self) -> List[str]:
        return self._services

    @services.setter
    def services(self, value: List[str]) -> None:
        self._services = value

    @property
    def access_level(self) -> AccessLevel:
        return self._access_level

    @access_level.setter
    def access_level(self, value: AccessLevel) -> None:
        self._access_level = value

    @property
    def token(self) -> Optional[uuid.UUID]:
        return self._token

    @token.setter
    def token(self, value: uuid) -> None:
        self._token = value

    def __str__(self) -> str:
        return "[Id: {}, Identity: {}, Nodes: {}, Services: {}, Access Level: {}, Token: {}]".format(self.id,
                                                                                                     self.identity,
                                                                                                     self.nodes,
                                                                                                     self.services,
                                                                                                     self.access_level.name,
                                                                                                     self.token)

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def cast_from(o: Authorization) -> 'AuthorizationImpl':
        if isinstance(o, AuthorizationImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Authorization interface")

    @property
    def expiration(self) -> int:
        return self._expiration


class PolicyStats:
    def __init__(self, authorization_entry_count: int = 0):
        self._authorization_entry_count = authorization_entry_count

    @property
    def authorization_entry_count(self):
        return self._authorization_entry_count

"""
class Policy(EnvironmentPolicy):

    def __init__(self):
        self._authorizations = []

        try:
            self._conn = sqlite3.connect(':memory:')
            self._conn.execute("CREATE TABLE authorizations(id varchar, identity varchar, node varchar, service varchar, access integer, token varchar)")
        except Error as e:
            print("Could not create an authenticator database. Reason: " + str(e))
            raise

    def __del__(self):
        self._conn.close()

    def reset(self):
        self._conn.execute("DELETE FROM authorizations")
        self._authorizations.clear()

    def create_authorization(self, identity: str, nodes: List[Union[str, Node]],
                             services: List[Union[str, Service]], access_level: AccessLevel, id: Optional[str] = None,
                             token: Optional[str] = None) -> Authorization:
        node_ids = [NodeImpl.cast_from(x).id if isinstance(x, Node) else x for x in nodes]
        service_ids = [ServiceImpl.cast_from(x).id if isinstance(x, Service) else x for x in services]

        auth_id = id
        if not auth_id:
            auth_id = str(uuid.uuid4())
        if not token:
            token = str(uuid.uuid4())
        auth = AuthorizationImpl(identity, node_ids, service_ids, access_level, auth_id, token)
        return auth

    # TODO stub authorizations are currently broken af
    def create_stub_authorization(self, identity: Optional[str] = None, nodes: Optional[List[Union[str, Node]]] = None,
                                  services: Optional[List[Union[str, Service]]] = None, access_level: Optional[AccessLevel] = AccessLevel.NONE) -> Authorization:
        if nodes:
            node_ids = [NodeImpl.cast_from(x).id if isinstance(x, Node) else x for x in nodes]
        else:
            node_ids = None

        if services:
            service_ids = [ServiceImpl.cast_from(x).id if isinstance(x, Service) else x for x in services]
        else:
            service_ids = None
        auth = AuthorizationImpl(identity, node_ids, service_ids, access_level)
        return auth

    def create_stub_from_authorization(self, authorization: Authorization) -> Authorization:
        other = AuthorizationImpl.cast_from(authorization)
        auth = AuthorizationImpl(other.identity, other.nodes, other.services, other.access_level)
        return auth

    def add_authorization(self, *authorizations: Authorization) -> None:
        for authorization in authorizations:
            authorization = AuthorizationImpl.cast_from(authorization)
            # make a cartesian product of all authorizations
            data = list(product([authorization.identity], authorization.nodes, authorization.services, [authorization.access_level.value]))

            auth_id = authorization.id
            # and store them in a database
            for d in data:
                auth_identity = d[0]
                auth_node = d[1]
                if isinstance(auth_node, NodeImpl):
                    auth_node = auth_node.id
                auth_service = d[2]
                if isinstance(auth_service, ServiceImpl):
                    auth_service = auth_service.id
                auth_access = d[3]
                # TODO somewhere here is lurking an option to bypass authorization process by creating stub Authorizations. This needs to be fixed
                self._conn.execute("INSERT INTO authorizations(id, identity, node, service, access, token) VALUES(?,?,?,?,?,?)", (auth_id, auth_identity, auth_node, auth_service, auth_access, str(authorization.token) if authorization.token else '*'))

    def decide(self, node: Union[str, Node], service: str, access_level: AccessLevel, authorization: Authorization) -> Tuple[bool, str]:
        authorization = AuthorizationImpl.cast_from(authorization)
        node_id: str
        if isinstance(node, str):
            node_id = node
        else:
            node_id = NodeImpl.cast_from(node).id
        # First check if the authorization is even valid for given parameters
        if (
                ("*" not in authorization.nodes and node_id not in authorization.nodes) or
                ("*" not in authorization.services and service not in authorization.services) or
                access_level.value > authorization.access_level.value
           ):
            return False, "Authorization not valid for given parameters"

        sql = '''SELECT COUNT(*) FROM authorizations WHERE (identity=? or identity=?) AND (node = ? OR node = ?) AND (service = ? OR service = ?) AND access >= ? AND (token=? OR token=?)'''
        cursor = self._conn.execute(sql, (authorization.identity, '*', node_id, '*', service, '*', int(access_level), str(authorization.token), '*'))
        count = cursor.fetchone()[0]

        if count != 0:
            return True, "Provided authorization is valid"
        else:
            return False, "Provided authorization does not match valid authorizations."

    def get_nodes(self, authorization: Authorization) -> List[str]:
        return AuthorizationImpl.cast_from(authorization).nodes

    def get_services(self, authorization: Authorization) -> List[str]:
        return AuthorizationImpl.cast_from(authorization).services

    def get_access_level(self, authorization: Authorization) -> AccessLevel:
        return AuthorizationImpl.cast_from(authorization).access_level

    def get_stats(self) -> PolicyStats:
        cursor = self._conn.execute("SELECT COUNT(*) FROM authorizations")
        authorization_entry_count = cursor.fetchone()[0]

        return PolicyStats(authorization_entry_count)

    # TODO what is the purpose of this, dangit?!
    def get_authorizations(self, node: Union[str, Node], service: str, access_level: AccessLevel = AccessLevel.NONE) -> List[Authorization]:
        if isinstance(node, Node):
            node_id = NodeImpl.cast_from(node).id
        else:
            node_id = node

        sql = '''SELECT id FROM authorizations WHERE node=?'''
        if service != '*':
            sql += ''' AND service = ?'''
            if access_level != AccessLevel.NONE:
                sql += " AND access = ?"
                cursor = self._conn.execute(sql, (node_id, service, int(access_level)))
            else:
                cursor = self._conn.execute(sql, (node_id, service))
        else:
            if access_level != AccessLevel.NONE:
                sql += " AND access = ?"
                cursor = self._conn.execute(sql, (node_id, int(access_level)))
            else:
                cursor = self._conn.execute(sql, (node_id,))

        ids = set()
        for id in cursor.fetchall():
            ids.add(id[0])

        return list(map(lambda x: AuthorizationImpl(x), ids))
"""

# ----------------------------------------------------------------------------------------------------------------------
# New version
# ----------------------------------------------------------------------------------------------------------------------


class Policy(EnvironmentPolicy):

    def __init__(self, configuration: EnvironmentConfiguration):
        self._config = configuration

    def create_authorization(self, identity: str, nodes: List[Union[str, Node]], services: List[Union[str, Service]],
                             access_level: AccessLevel, id: Optional[str] = None,
                             token: Optional[str] = None) -> Optional[Authorization]:

        if not nodes or not services:
            return None

        auth = AuthorizationImpl(identity, nodes, services, access_level, id, token)

        if len(nodes) > 1 or services == ["*"]: # federated, temporary solution
            return auth

        actual_node = nodes[0] if isinstance(nodes[0], Node) else self._config.general.get_object_by_id(nodes[0], Node)
        # if nodes is a [str], is it id, ip or else??

        for service in services:
            actual_service = service if isinstance(service, Service)\
                else actual_node.services.get(service)
            if isinstance(actual_service, PassiveServiceImpl):
                actual_service.add_active_authorization(auth)

        return auth



    def create_stub_authorization(self, identity: Optional[str] = None, nodes: Optional[List[Union[str, Node]]] = None,
                                  services: Optional[List[Union[str, Service]]] = None,
                                  access_level: AccessLevel = AccessLevel.NONE) -> Authorization:
        pass

    def create_stub_from_authorization(self, authorization: Authorization) -> Authorization:
        pass

    def add_authorization(self, *authorizations: Authorization) -> None:
        pass

    def get_authorizations(self, node: Union[str, Node], service: str, access_level: AccessLevel = AccessLevel.NONE) -> \
    List[Authorization]:
        pass

    def decide(self, node: Union[str, Node], service: str, access_level: AccessLevel, authorization: Authorization) -> \
    Tuple[bool, str]:

        actual_node = node if isinstance(node, Node) else self._config.general.get_object_by_id(node, Node)

        actual_service = actual_node.services.get(service)

        if not actual_service:
            return False, "Service does not exist on node."

        retval = None

        if isinstance(actual_service, PassiveServiceImpl):
            retval = actual_service.assess_authorization(Authorization, access_level)

        if not retval:
            return False, "Invalid service type."

        return retval




    def get_nodes(self, authorization: Authorization) -> List[str]:
        return AuthorizationImpl.cast_from(authorization).nodes

    def get_services(self, authorization: Authorization) -> List[str]:
        return AuthorizationImpl.cast_from(authorization).services

    def get_access_level(self, authorization: Authorization) -> AccessLevel:
        return AuthorizationImpl.cast_from(authorization).access_level


class AuthenticationTokenImpl(AuthenticationToken):

    def __init__(self, token_type: AuthenticationTokenType, security: AuthenticationTokenSecurity, identity: str,
                 is_local: bool):
        self._type = token_type
        self._security = security
        self._identity = identity
        self._is_local = is_local

        # create data according to the security
        # TODO: Until the concept of sealed data is introduced in the code, all is assumed to be OPEN
        value = uuid.uuid4()
        self._content = DataImpl(value, "")

    @property
    def type(self) -> AuthenticationTokenType:
        return self._type

    @property
    def is_local(self):
        return self._is_local

    @property
    def security(self) -> AuthenticationTokenSecurity:
        return self._security

    @property
    def identity(self) -> str:
        return self._identity

    def copy(self) -> Optional[AuthenticationToken]:
        pass # TODO different uuid needed????

    @property
    def content(self) -> Optional[Data]:
        return self._content

    @staticmethod
    def is_local_instance(obj: AuthenticationToken):
        if isinstance(obj, AuthenticationTokenImpl):
            return obj.is_local
        return False


class AuthenticationTargetImpl(AuthenticationTarget):
    def __init__(self, tokens: List[AuthenticationTokenType], service: Optional[str] = None,
                 ip: Optional[IPAddress] = None):
        self._address = ip
        self._service = service
        self._tokens = tokens

    @property
    def address(self) -> Optional[IPAddress]:
        return self._address

    @property
    def service(self) -> str:
        return self._service

    @property
    def tokens(self) -> List[AuthenticationTokenType]:
        return self._tokens

    @address.setter
    def address(self, ip: IPAddress):
        self._address = ip

    @service.setter
    def service(self, serv: str):
        self._service = serv


class AccessSchemeImpl(AccessScheme):
    def __init__(self):
        self._providers = []
        self._authorizations = []
        self._identities = []

    def add_provider(self, provider: AuthenticationProvider):
        self._providers.append((provider, len(self._providers)))

    def add_identity(self, identity: str):
        self._identities.append(identity)

    def add_authorization(self, auth: Authorization):
        self._authorizations.append(auth)

    @property
    def factors(self) -> List[Tuple[AuthenticationProvider, int]]:
        return self._providers
    # TODO : what is the number?? I will just use order ATM

    @property
    def identities(self) -> List[str]:
        return self._identities

    @property
    def authorizations(self) -> List[Authorization]:
        return self._authorizations


class AuthenticationProviderImpl(AuthenticationProvider):

    def __init__(self, provider_type: AuthenticationProviderType, token_type: AuthenticationTokenType,
                 security: AuthenticationTokenSecurity, ip: Optional[IPAddress], timeout: int):

        self._provider_type = provider_type
        self._token_type = token_type
        self._security = security
        self._timeout = timeout

        self._tokens = set()
        self._target = self._create_target()

        if provider_type != AuthenticationProviderType.LOCAL and ip is None:
            raise RuntimeError("Non-local provider needs ip address")
        self._set_address(ip)

    @property
    def type(self) -> AuthenticationProviderType:
        return self._provider_type

    @property
    def target(self) -> AuthenticationTarget:
        return self._target

    @property
    def token_type(self):
        return self._token_type

    @property
    def security(self):
        return self._security

    def token_is_registered(self, token: AuthenticationToken):
        for t in self._tokens:
            if t.identity == token.identity and t.content.id == token.content.id\
                    and t.content.owner == token.content.owner\
                    and token.content.description == t.content.description:
                return True
        return False

    def add_token(self, token: AuthenticationToken):
        self._tokens.add(token)

    def _create_target(self):
        # TODO: inherit from provider? or should we do something else?
        return AuthenticationTargetImpl([self._token_type])

    def set_service(self, srv_id: str):

        if self._target.service is None:
            self._target.service = srv_id
        else:
            raise RuntimeError  # TODO check what should be done here, exception might be too harsh

    def _set_address(self, ip: IPAddress):
        if self._target.address is None:
            self._target.address = ip
        else:
            raise RuntimeError
