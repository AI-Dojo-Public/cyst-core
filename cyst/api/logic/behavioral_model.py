from abc import ABC, abstractmethod
from dataclasses import dataclass
from deprecated.sphinx import versionadded, versionchanged
from enum import Enum
from typing import Callable, List, Tuple, Union

from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.platform_specification import PlatformSpecification, PlatformType
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.message import Request, Response
from cyst.api.logic.action import Action
from cyst.api.logic.composite_action import CompositeActionManager
from cyst.api.network.node import Node
from cyst.api.utils.duration import Duration


class BehavioralModel(ABC):

    @abstractmethod
    async def action_flow(self, message: Request) -> Tuple[Duration, Response]:
        pass

    @abstractmethod
    async def action_effect(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        pass

    @abstractmethod
    def action_components(self, message: Union[Request, Response]) -> List[Action]:
        pass


@versionchanged(version="0.6.0", reason="Added platform specification")
@dataclass
class BehavioralModelDescription:
    """
    TODO: Add text

    :param namespace: A namespace in which all interpreted actions belong to. An arbitrary namespace nesting is
        supported through the dot notation (e.g., "a.b.c" namespaces and actions of the form "a.b.c.action_n").
    :type namespace: str

    :param description: A textual description of the action interpreter. The description should introduce the behavioral
        model that the interpreter implements, so that the users can decide whether to use it or not.
    :type description: str

    :param creation_fn: A factory function that can create the interpreter.
    :type creation_fn: Callable[[EnvironmentConfiguration, EnvironmentResources, EnvironmentPolicy, EnvironmentMessaging, CompositeActionManager], ActionInterpreter]

    :param platform: A platform or platforms for which this behavioral model is constructed. Different modules can
        support one namespace for different platforms.
    :type platform: Union[PlatformSpecification, List[PlatformSpecification]]

    """
    namespace: str
    description: str
    creation_fn: Callable[[EnvironmentConfiguration, EnvironmentResources, EnvironmentPolicy, EnvironmentMessaging, EnvironmentInfrastructure, CompositeActionManager], BehavioralModel]
    platform: Union[PlatformSpecification, List[PlatformSpecification]] = PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST")
