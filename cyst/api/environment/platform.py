from abc import abstractmethod, ABC
from asyncio import Task
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Tuple, List

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.clock import Clock
from cyst.api.environment.configuration import EnvironmentConfiguration, GeneralConfiguration, ActionConfiguration, ExploitConfiguration
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
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

    @property
    @abstractmethod
    def configuration(self) -> EnvironmentConfiguration:
        pass

    @abstractmethod
    def configure(self, *config_item: ConfigItem) -> 'Platform':
        pass

    @property
    @abstractmethod
    def messaging(self) -> EnvironmentMessaging:
        pass

    @abstractmethod
    def collect_messages(self) -> List[Message]:
        pass

    @abstractmethod
    async def process(self, time: int) -> Task:
        pass

    @property
    @abstractmethod
    def clock(self) -> Clock:
        pass


@dataclass
class PlatformDescription:
    specification: PlatformSpecification
    description: str
    creation_fn: Callable[[PlatformInterface, GeneralConfiguration, EnvironmentResources, ActionConfiguration, ExploitConfiguration, EnvironmentInfrastructure], Platform]