import sqlite3
import uuid

from enum import IntEnum
from itertools import product
from typing import List, Tuple, Union, Optional
from sqlite3 import Error

from netaddr import IPAddress

from cyst.api.configuration.logic.access import AccessLevel
from cyst.api.host.service import Service
from cyst.api.logic.access import Authorization, AuthenticationToken, AuthenticationTokenSecurity, \
    AuthenticationTokenType, AuthenticationProvider, AuthenticationTarget, AuthenticationProviderType
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.logic.data import Data
from cyst.api.network.node import Node

from cyst.core.network.node import NodeImpl
from cyst.core.host.service import ServiceImpl
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
        self._d = value

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
        return "[Id: {}, Identity: {}, Nodes: {}, Services: {}, Access Level: {}, Token: {}]".format(self.id, self.identity, self.nodes, self.services, self.access_level.name, self.token)

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def cast_from(o: Authorization) -> 'AuthorizationImpl':
        if isinstance(o, AuthorizationImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Authorization interface")


class PolicyStats:
    def __init__(self, authorization_entry_count: int = 0):
        self._authorization_entry_count = authorization_entry_count

    @property
    def authorization_entry_count(self):
        return self._authorization_entry_count


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


# ----------------------------------------------------------------------------------------------------------------------
# New version
# ----------------------------------------------------------------------------------------------------------------------

class AuthenticationTokenImpl(AuthenticationToken):

    def __init__(self, type: AuthenticationTokenType, security: AuthenticationTokenSecurity, identity: str):
        self._type = type
        self._security = security
        self._identity = identity

        # create data according to the security
        # TODO: Until the concept of sealed data is introduced in the code, all is assumed to be OPEN
        value = uuid.uuid4()
        self._content = DataImpl(value, "")

    @property
    def type(self) -> AuthenticationTokenType:
        return self._type

    @property
    def security(self) -> AuthenticationTokenSecurity:
        return self._security

    @property
    def identity(self) -> str:
        return self._identity

    def copy(self) -> Optional['AuthenticationToken']:
        pass

    @property
    def content(self) -> Optional[Data]:
        return self._content


class AuthenticationTargetImpl(AuthenticationTarget):
    def __init__(self, tokens: List[AuthenticationTokenType], service: Optional[str] = None, ip: Optional[IPAddress]=None):
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


class AuthenticationProviderImpl(AuthenticationProvider):

    def __init__(self, provider_type: AuthenticationProviderType, token_type: AuthenticationTokenType,
                 security: AuthenticationTokenSecurity, timeout: int):

        self._provider_type = provider_type
        self._token_type = token_type
        self._security = security
        self._timeout = timeout

        self._tokens = set()
        self._target  = self._create_target()


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

    def add_token(self, token: AuthenticationToken):
        self._tokens.add(token)

    def _create_target(self):
        # TODO: inherit from provider? or should we do something else?
        return  AuthenticationTargetImpl([self._token_type])

    def set_service(self, id: str):

        if self._target.service is None:
            self._target.service = id
        else:
            raise RuntimeError # TODO check what should be done here, exception might bee too harsh

    def set_address(self, ip: IPAddress):
        pass # TODO, where does the ip come from??