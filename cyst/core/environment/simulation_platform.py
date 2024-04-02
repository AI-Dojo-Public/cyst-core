# The implementation of a CYST simulation platform that is used to get rid of unnecessary branching in code.
from typing import List

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.environment import Environment
from cyst.api.environment.message import Message
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.platform import Platform
from cyst.api.environment.resources import EnvironmentResources


class CYSTSimulationPlatform (Platform):
    def __init__(self, environment: Environment):
        self._environment = environment

    # Both init and termination calls are handled by the CYST top-level environment objects
    def init(self) -> bool:
        pass

    def terminate(self) -> bool:
        pass

    def configure(self, *config_item: ConfigItem) -> 'Platform':
        self._environment.configure(*config_item)
        return self

    @property
    def messaging(self) -> EnvironmentMessaging:
        return self._environment.messaging

    @property
    def resources(self) -> EnvironmentResources:
        return self._environment.resources

    def collect_messages(self) -> List[Message]:
        pass