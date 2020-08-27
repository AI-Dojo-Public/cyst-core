from abc import ABC, abstractmethod
from semver import VersionInfo
from typing import Set, Tuple, NamedTuple, Callable, Dict, Any, Optional

from cyst.api.logic.access import AccessLevel
from cyst.api.utils.tag import Tag


class Service(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def owner(self) -> str:
        pass

    @property
    @abstractmethod
    def service_access_level(self) -> AccessLevel:
        pass

    @property
    @abstractmethod
    def passive_service(self) -> 'PassiveService':
        pass

    @property
    @abstractmethod
    def active_service(self) -> 'ActiveService':
        pass


class ActiveService(ABC):

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def process_message(self, message) -> Tuple[bool, int]:
        pass


class ActiveServiceDescription(NamedTuple):
    from cyst.api.environment.messaging import EnvironmentMessaging

    name: str
    description: str
    # TODO services are currently called with Dict[str, Any] for configuration. In the future, they should provide some
    #      information about their configuration
    creation_fn: Callable[[EnvironmentMessaging, Optional[Dict[str, Any]]], ActiveService]


class PassiveService(Service, ABC):

    @property
    @abstractmethod
    def version(self) -> VersionInfo:
        pass

    @property
    @abstractmethod
    def tags(self) -> Set[Tag]:
        pass

    @property
    @abstractmethod
    def enable_session(self) -> bool:
        pass

    @property
    @abstractmethod
    def session_access_level(self) -> AccessLevel:
        pass

    @property
    @abstractmethod
    def local(self) -> bool:
        pass
