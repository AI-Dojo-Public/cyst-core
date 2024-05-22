from abc import ABC, abstractmethod
from enum import Enum
from typing import Union, Optional, Type
from urllib.parse import ParseResult


from cyst.api.host.service import ActiveService

class ResourcePersistence(Enum):
    """
    Resources can be created in one of the two modes - transient and persistent. In the transient mode, they are
    opened and closed for each operation on them. In the persistent mode, they get opened on the first operation
    and must be closed via the :func:`release_resource` function.

    Possible values:
        :TRANSIENT: Open/close on each operation.
        :PERSISTENT: Stay opened after the first operation.

    """
    TRANSIENT = 0
    PERSISTENT = 1


class Resource(ABC):
    """
    Resource interface represents an interface that is user-facing. A user does not interact with the resource directly,
    but is instead using the :class:`ExternalResources` interface. Therefore, this interface provides only some minimal
    information about the resource.
    """
    @property
    @abstractmethod
    def path(self) -> str:
        """
        The URL of the resource. Technically, many different resources can share the same URL and be differentiated just
        by the parameters that are provided with particular operations on the :class:`ExternalResources` interface.
        Therefore, this property is only informative.
        """

    @property
    @abstractmethod
    def persistence(self) -> ResourcePersistence:
        """
        The persistence setting of the resource.
        """


class ResourceImpl(Resource, ABC):
    """
    This interface represents an implementation of a resource that is used by the :class:`ExternalResource` interface.
    Any new or custom resources that are added to the system must inherit from both :class:`Resource` and
    :class:`ResourceImpl`.
    """
    @abstractmethod
    def init(self, path: ParseResult, params: Optional[dict[str, str]] = None, persistence: ResourcePersistence = ResourcePersistence.TRANSIENT) -> bool:
        """
        This function is called when the resource is initialized after being created.

        :param path: The result of urllib.parse() call on the URL. The scheme is always guaranteed to be the same as
            the one used when this resource was registered.
        :type path: ParseResult

        :param params: Arbitrary parameters that may be required for resource initialization. If the resource is created
            implicitly via the ExternalResources interface, these parameters are shared with the call to
            :func:`send`/:func:`receive`.
        :type params: Optional[dict[str, str]]

        :param persistence: Persistence of a result. Implicitly created resources are always transient.
        :type persistence: ResourcePersistence

        :return: True if the resource was successfully created and False otherwise.
        """

    @abstractmethod
    def open(self) -> None:
        """
        This function is called prior to send/receive functions. It should prepare the resource for interactions.

        :return: None
        """

    @abstractmethod
    def close(self) -> None:
        """
        This function closes the resource. Any interaction after closing should fail. Close is either called immediately
        after :func:`send`/:func:`receive` operation for transient resources, or called when the resource is released
        for persistent ones.

        :return: None
        """

    @abstractmethod
    async def send(self, data: str, params: Optional[dict[str, str]] = None) -> int:
        """
        This function sends the data to the resource, e.g., writes to the socket, writes to a file, or inserts into
        a database. Due to its async nature, you should utilize the async I/O operations, as the sync ones can
        disturb the execution of the rest of the processing.

        :param data: The data that should be written.
        :type data: str

        :param params: Arbitrary parameters that modify the send operation. If the resource was implicitly created,
            these parameters may contain ones that are related to resource creation.
        :type params: Optional[dict[str, str]]

        :return: The number of characters that were actually written, even though the expectation here is that this
            function sends all the data or fails.
        """

    @abstractmethod
    async def receive(self, params: Optional[dict[str, str]] = None) -> Optional[str]:
        """
        This function read the data from the resource. Due to its async nature, you should utilize the async I/O
        operations, as the sync ones can disturb the execution of the rest of the processing.

        :param params: Arbitrary parameters that modify the receive operation. If the resource was implicitly created,
            these parameters may contain ones that are related to resource creation.
        :type params: Optional[dict[str, str]]

        :return: The data received from the resource or None if nothing was available or expected, e.g., HEAD HTTP
            request.
        """


class ExternalResources(ABC):

    @abstractmethod
    def register_resource(self, scheme: str, resource: Union[Type, ResourceImpl]) -> bool:
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
