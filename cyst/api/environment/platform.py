from abc import abstractmethod, ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources


class PlatformType(Enum):
    SIMULATION = auto()
    EMULATION = auto()


@dataclass(frozen=True)
class PlatformSpecification:
    type: PlatformType
    provider: str


class Platform(ABC):
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


@dataclass
class PlatformDescription:
    specification: PlatformSpecification
    description: str
    creation_fn: Callable[['Environment'], Platform]
