from abc import ABC, abstractmethod
from typing import Tuple, Optional

from cyst.api.environment.message import Request, Response, Message
from cyst.api.host.service import Service
from cyst.api.network.node import Node


class PlatformInterface(ABC):
    """
    An interface that enables platforms to communicate with the core to elicit effects.
    """

    @abstractmethod
    def execute_task(self, task: Message, service: Optional[Service] = None, node: Optional[Node] = None, delay: float = 0.0) -> Tuple[bool, float]:
        """
        Instruct the core to execute included action with the appropriate behavioral model. The function signature
        follows the signature of :func:`cyst.api.logic.behavioral_model.action_effect`.

        :param task: The message containing the action. In virtually all cases this will be messages of type
            :class:`MessageType.REQUEST`, however, there is nothing preventing a platform to call behavioral models
            for actions on responses.
        :type task: Message

        :param service: A service on which the action should be executed. The platform is free to ignore this parameter
            if its associated behavioral model does not require it.
        :type service: Optional[Service]

        :param node: A node on which the action should be executed. The platform is free to ignore this parameter
            if its associated behavioral model does not require it.
        :type node: Optional[Node]

        :param delay: A delay before the execution of the action.
        :type delay: float

        :return: A tuple indicating whether the action was successfully executed and how long the execution took.
        """

    @abstractmethod
    def process_response(self, response: Response) -> Tuple[bool, int]:
        pass
