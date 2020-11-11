from abc import ABC, abstractmethod
from dataclasses import dataclass
from semver import VersionInfo
from typing import Set, Tuple, NamedTuple, Callable, Dict, Any, Optional, List, Union

from cyst.api.logic.access import AccessLevel, AuthorizationConfig
from cyst.api.logic.data import DataConfig
from cyst.api.utils.tag import Tag
from cyst.api.utils.configuration import ConfigItem


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


@dataclass
class ActiveServiceConfig(ConfigItem):
    type: str
    name: str
    owner: str
    access_level: AccessLevel
    configuration: Optional[Dict[str, Any]] = None


class ActiveService(ABC):

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def process_message(self, message) -> Tuple[bool, int]:
        pass


class ActiveServiceDescription(NamedTuple):
    from cyst.api.environment.messaging import EnvironmentMessaging
    from cyst.api.environment.resources import EnvironmentResources

    name: str
    description: str
    # TODO services are currently called with Dict[str, Any] for configuration. In the future, they should provide some
    #      information about their configuration
    creation_fn: Callable[[EnvironmentMessaging, EnvironmentResources, Optional[Dict[str, Any]]], ActiveService]


@dataclass
class PassiveServiceCfg(ConfigItem):
    type: str
    owner: str
    version: str
    local: bool
    access_level: AccessLevel
    public_data: Optional[List[Union[DataConfig, str]]] = None
    private_data: Optional[List[Union[DataConfig, str]]] = None
    public_authorizations: Optional[List[Union[AuthorizationConfig, str]]] = None
    private_authorizations: Optional[List[Union[AuthorizationConfig, str]]] = None


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
