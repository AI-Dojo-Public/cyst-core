from abc import ABC, abstractmethod

from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.control import EnvironmentControl
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.policy import EnvironmentPolicy


class Environment(ABC):

    @property
    @abstractmethod
    def configuration(self) -> EnvironmentConfiguration:
        pass

    @property
    @abstractmethod
    def control(self) -> EnvironmentControl:
        pass

    @property
    @abstractmethod
    def messaging(self) -> EnvironmentMessaging:
        pass

    @property
    @abstractmethod
    def resources(self) -> EnvironmentResources:
        pass

    @property
    @abstractmethod
    def policy(self) -> EnvironmentPolicy:
        pass

    @classmethod
    def create(cls) -> 'Environment':
        import cyst.core.environment.environment
        return cyst.core.environment.environment.create_environment()
