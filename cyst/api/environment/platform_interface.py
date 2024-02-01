from abc import ABC, abstractmethod
from typing import Tuple

from cyst.api.environment.message import Request, Response


class PlatformInterface(ABC):

    @abstractmethod
    def execute_request(self, request: Request) -> Tuple[bool, int]:
        pass

    @abstractmethod
    def process_response(self, response: Response) -> Tuple[bool, int]:
        pass
