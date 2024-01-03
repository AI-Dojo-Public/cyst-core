from abc import ABC, abstractmethod
from dataclasses import dataclass
from deprecated.sphinx import versionadded
from enum import Enum
from typing import Callable, List, Tuple, Union

from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.message import Request, Response
from cyst.api.logic.action import Action
from cyst.api.logic.composite_action import CompositeActionManager
from cyst.api.network.node import Node


class BehavioralModel(ABC):

    @abstractmethod
    async def action_flow(self, message: Request) -> Tuple[int, Response]:
        pass

    @abstractmethod
    def action_effect(self, message: Request, node: Node) -> Tuple[int, Response]:
        pass

    @abstractmethod
    def action_components(self, message: Union[Request, Response]) -> List[Action]:
        pass


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

    """
    namespace: str
    description: str
    creation_fn: Callable[[EnvironmentConfiguration, EnvironmentResources, EnvironmentPolicy, EnvironmentMessaging, CompositeActionManager], BehavioralModel]
