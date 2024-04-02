from abc import abstractmethod, ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Tuple, List

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.message import Message
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.platform_interface import PlatformInterface
from cyst.api.environment.platform_specification import PlatformSpecification
from cyst.api.environment.resources import EnvironmentResources


class Platform(ABC):
    @abstractmethod
    def init(self) -> bool:
        pass

    @abstractmethod
    def terminate(self) -> bool:
        pass

    @abstractmethod
    def configure(self, *config_item: ConfigItem) -> 'Platform':
        pass

    @property
    @abstractmethod
    def messaging(self) -> EnvironmentMessaging:
        pass

    @property
    @abstractmethod
    def resources(self) -> EnvironmentResources:
        pass

    @abstractmethod
    def collect_messages(self) -> List[Message]:
        pass


@dataclass
class PlatformDescription:
    specification: PlatformSpecification
    description: str
    creation_fn: Callable[[PlatformInterface, EnvironmentConfiguration, EnvironmentMessaging, EnvironmentResources], Platform]