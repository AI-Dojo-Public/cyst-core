from abc import ABC, abstractmethod
from enum import Enum
from typing import Union, Optional, Callable

from cyst.api.host.service import Service


class ResourcePersistence(Enum):
    TRANSIENT = 0
    PERSISTENT = 1


class Resource(ABC):
    def path(self) -> str:
        pass

    def persistence(self) -> ResourcePersistence:
        pass


class ExternalResources(ABC):

    def custom_resource(self, init: Callable[[dict[str, str]], bool],
                              open: Callable[[], int],
                              close: Callable[[], int],
                              send: Callable[[dict[str, str]], int],
                              receive: Callable[[], str]):
        pass

    def persistent_resource(self, path: str, params: dict[str, str]) -> Resource:
        pass

    def release_resource(self, resource: Resource) -> None:
        pass

    def send(self, resource: Union[str, Resource], params: Optional[dict[str, str]], virtual_duration: int = 0, timeout: int = 0) -> None:
        pass

    def fetch(self, resource: Union[str, Resource], params: Optional[dict[str, str]], virtual_duration: int = 0, timeout: int = 0, service: Optional[Service] = None) -> Optional[str]:
        pass
