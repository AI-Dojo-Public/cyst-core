from abc import ABC, abstractmethod
from typing import Tuple, Optional

from cyst.api.environment.message import Request, Response
from cyst.api.network.node import Node


class PlatformInterface(ABC):

    @abstractmethod
    def execute_request(self, request: Request, node: Optional[Node] = None) -> Tuple[bool, int]:
        pass

    @abstractmethod
    def process_response(self, response: Response) -> Tuple[bool, int]:
        pass
