from abc import ABC, abstractmethod
from typing import Tuple, Optional

from cyst.api.environment.message import Request, Response, Message
from cyst.api.host.service import Service
from cyst.api.network.node import Node


class PlatformInterface(ABC):

    @abstractmethod
    def execute_task(self, task: Message, service: Optional[Service] = None, node: Optional[Node] = None, delay: int = 0) -> Tuple[bool, int]:
        pass

    @abstractmethod
    def process_response(self, response: Response) -> Tuple[bool, int]:
        pass
