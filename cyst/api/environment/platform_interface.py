from abc import ABC, abstractmethod
from typing import Tuple, Optional

from cyst.api.environment.message import Request, Response, Message
from cyst.api.network.node import Node

# While this is an unfortunate break of encapsulation between the core and the API, the platform may often need full
# access to message internals, so we are currently sticking with it.
from cyst.core.environment.message import MessageImpl

class PlatformInterface(ABC):

    @abstractmethod
    def execute_request(self, request: Request, node: Optional[Node] = None) -> Tuple[bool, int]:
        pass

    @abstractmethod
    def process_response(self, response: Response) -> Tuple[bool, int]:
        pass

    @abstractmethod
    def get_message_internals(self, message: Message) -> MessageImpl:
        pass
