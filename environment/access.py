import sqlite3
import uuid

from enum import IntEnum
from itertools import product
from typing import List, Tuple
from sqlite3 import Error

from utils.singleton import Singleton


class AccessLevel(IntEnum):
    NONE = 0,
    LIMITED = 1,
    ELEVATED = 2


class Authorization:
    def __init__(self, identity: str = "", nodes: List[str] = None, services: List[str] = None, access_level: AccessLevel = AccessLevel.NONE, token: uuid = None):
        if services is None or not services:
            services = ["*"]
        if nodes is None or not nodes:
            nodes = ["*"]
        self._identity = identity
        self._nodes = nodes
        self._services = services
        self._access_level = access_level
        self._token = token

    def __eq__(self, other: 'Authorization') -> bool:
        return (
                self.identity == other.identity and
                self.nodes == other.nodes and
                self.services == other.services and
                self.access_level == other.access_level and
                self.token == other.token
        )

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
    def token(self) -> uuid:
        return self._token

    @token.setter
    def token(self, value: uuid) -> None:
        self._token = value

    def __str__(self) -> str:
        return "[Identity: {}, Nodes: {}, Services: {}, Access Level: {}, Token: {}]".format(self.identity, self.nodes, self.services, self.access_level.name, self.token)

    def __repr__(self) -> str:
        return self.__str__()


class PolicyStats:
    def __init__(self, authorization_entry_count: int = 0):
        self._authorization_entry_count = authorization_entry_count

    @property
    def authorization_entry_count(self):
        return self._authorization_entry_count


class Policy(metaclass=Singleton):
    def __init__(self):
        self._authorizations = []

        try:
            self._conn = sqlite3.connect(':memory:')
            self._conn.execute("CREATE TABLE authorizations(id varchar, node varchar, service varchar, access integer, token varchar)")
        except Error as e:
            print("Could not create an authenticator database. Reason: " + str(e))
            raise

    def __del__(self):
        self._conn.close()

    def reset(self):
        self._conn.execute("DELETE FROM authorizations")
        self._authorizations.clear()

    def add_authorization(self, *authorizations: Authorization) -> None:
        for authorization in authorizations:
            # make a cartesian product of all authorizations
            data = list(product([authorization.identity], authorization.nodes, authorization.services, [authorization.access_level.value]))

            # and store them in a database
            for d in data:
                self._conn.execute("INSERT INTO authorizations(id, node, service, access, token) VALUES(?,?,?,?,?)", (d[0], d[1], d[2], d[3], str(authorization.token) if authorization.token else '*'))

    def decide(self, node: str, service: str, access_level: AccessLevel, authorization: Authorization) -> Tuple[bool, str]:
        # First check if the authorization is even valid for given parameters
        if (
                node not in authorization.nodes or
                service not in authorization.services or
                access_level.value > authorization.access_level.value
           ):
            return False, "Authorization not valid for given parameters"

        sql = '''SELECT COUNT(*) FROM authorizations WHERE (id=? or id=?) AND (node = ? OR node = ?) AND (service = ? OR service = ?) AND access >= ? AND (token=? OR token=?)'''
        cursor = self._conn.execute(sql, (authorization.identity, '*', node, '*', service, '*', int(access_level), str(authorization.token), '*'))
        count = cursor.fetchone()[0]

        if count != 0:
            return True, "Provided authorization is valid"
        else:
            return False, "Provided authorization does not match valid authorizations."

    def get_stats(self) -> PolicyStats:
        cursor = self._conn.execute("SELECT COUNT(*) FROM authorizations")
        authorization_entry_count = cursor.fetchone()[0]

        return PolicyStats(authorization_entry_count)
