from abc import ABC, abstractmethod
from enum import Enum
from typing import Union, Optional
from urllib.parse import ParseResult


from cyst.api.host.service import ActiveService

class ResourcePersistence(Enum):
    TRANSIENT = 0
    PERSISTENT = 1


class Resource(ABC):
    @property
    @abstractmethod
    def path(self) -> str:
        pass

    @property
    @abstractmethod
    def persistence(self) -> ResourcePersistence:
        pass


class ResourceImpl(Resource, ABC):
    @abstractmethod
    def init(self, path: ParseResult, params: Optional[dict[str, str]] = None, persistence: ResourcePersistence = ResourcePersistence.TRANSIENT) -> bool:
        pass

    @abstractmethod
    def open(self) -> int:
        pass

    @abstractmethod
    def close(self) -> int:
        pass

    @abstractmethod
    async def send(self, data: str, params: Optional[dict[str, str]] = None) -> int:
        pass

    @abstractmethod
    async def receive(self, params: Optional[dict[str, str]] = None) -> Optional[str]:
        pass


class ExternalResources(ABC):

    @abstractmethod
    def register_resource(self, scheme: str, resource: ResourceImpl) -> bool:
        pass

    @abstractmethod
    def create_resource(self, path: str, params: Optional[dict[str, str]] = None, persistence: ResourcePersistence = ResourcePersistence.TRANSIENT) -> Resource:
        pass

    @abstractmethod
    def release_resource(self, resource: Resource) -> None:
        pass

    @abstractmethod
    async def send_async(self, resource: Union[str, Resource], data: str, params: Optional[dict[str, str]] = None, timeout: float = 0.0) -> None:
        pass

    @abstractmethod
    def send(self, resource: Union[str, Resource], data: str, params: Optional[dict[str, str]] = None, timeout: float = 0.0, callback_service: Optional[ActiveService] = None) -> None:
        pass

    @abstractmethod
    async def fetch_async(self, resource: Union[str, Resource], params: Optional[dict[str, str]] = None, timeout: float = 0.0) -> Optional[str]:
        pass

    @abstractmethod
    def fetch(self, resource: Union[str, Resource], params: Optional[dict[str, str]] = None, timeout: float = 0.0, callback_service: Optional[ActiveService] = None) -> None:
        pass
