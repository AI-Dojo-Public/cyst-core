from abc import ABC, abstractmethod
from enum import Enum
from netaddr import IPAddress
from typing import Any, Optional, Union

from cyst.api.network.session import Session
from cyst.api.logic.access import Authorization
from cyst.api.logic.action import Action


class MessageType(Enum):
    TIMEOUT = 0
    REQUEST = 1
    RESPONSE = 2


class StatusOrigin(Enum):
    NETWORK = 0
    NODE = 1
    SERVICE = 2
    SYSTEM = 99


class StatusValue(Enum):
    SUCCESS = 0
    FAILURE = 1
    ERROR = 2


class Status:
    def __init__(self, origin=None, value=None):
        self._origin = origin
        self._value = value

    def __str__(self) -> str:
        return "({}, {})".format(self._origin.name, self._value.name)

    def __eq__(self, other: 'Status') -> bool:
        return self._origin == other.origin and self._value == other.value

    @property
    def origin(self) -> StatusOrigin:
        return self._origin

    @property
    def value(self) -> StatusValue:
        return self._value


class Message(ABC):

    @property
    @abstractmethod
    def id(self) -> int:
        pass

    @property
    @abstractmethod
    def type(self) -> MessageType:
        pass

    @property
    @abstractmethod
    def src_ip(self) -> Optional[IPAddress]:
        pass

    @property
    @abstractmethod
    def dst_ip(self) -> Optional[IPAddress]:
        pass

    @property
    @abstractmethod
    def src_service(self):
        pass

    @property
    @abstractmethod
    def dst_service(self):
        pass

    @property
    @abstractmethod
    def session(self) -> Session:
        pass

    @property
    @abstractmethod
    def authorization(self) -> Authorization:
        pass

    @property
    @abstractmethod
    def ttl(self):
        pass


class Request(Message, ABC):

    @property
    @abstractmethod
    def action(self) -> Action:
        pass


class Response(Message, ABC):

    @property
    @abstractmethod
    def status(self):
        pass

    @property
    @abstractmethod
    def content(self):
        pass
