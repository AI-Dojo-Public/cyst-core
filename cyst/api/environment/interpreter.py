from abc import ABC, abstractmethod
from typing import Callable, List, Tuple
from dataclasses import dataclass

from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.stores import ActionStore
from cyst.api.environment.message import Request, Response
from cyst.api.network.node import Node


class ActionInterpreter(ABC):
    """
    An action interpreter provides a semantic to the actions. It analyzes the incoming requests and then make
    appropriate changes in the environment and prepares responses that are sent back to the requests' origin.
    """
    @abstractmethod
    def evaluate(self, message: Request, node: Node) -> Tuple[int, Response]:
        """
        Evaluates the request.

        :param message: The request containing an action to be done.
        :type message: Request

        :param node: An instance of the node, where the message ended.
        :type node: Node

        :return: A tuple indicating the length of processing in the simulated time units and the Response that should
            be sent to the origin.
        """


@dataclass
class ActionInterpreterDescription:
    """ A definition of an action interpreter.

    :param namespace: A namespace in which all interpreted actions belong to. An arbitrary namespace nesting is
        supported through the dot notation (e.g., "a.b.c" namespaces and actions of the form "a.b.c.action_n").
    :type namespace: str

    :param description: A textual description of the action interpreter. The description should introduce the behavioral
        model that the interpreter implements, so that the users can decide whether to use it or not.
    :type description: str

    :param creation_fn: A factory function that can create the interpreter.
    :type creation_fn: Callable[[EnvironmentConfiguration, EnvironmentResources, EnvironmentPolicy, EnvironmentMessaging], ActionInterpreter]

    """
    namespace: str
    description: str
    creation_fn: Callable[[EnvironmentConfiguration, EnvironmentResources, EnvironmentPolicy, EnvironmentMessaging], ActionInterpreter]
