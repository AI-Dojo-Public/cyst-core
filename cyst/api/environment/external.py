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
    """
    External resources represent any resources that are not part of the simulation/emulation runs, such as files,
    REST APIs, databases, etc. To maintain a sensible and consistent relation to underlying platforms and their time,
    all such resources must be handled through this interface.

    .. warning::
        Due to technical reasons related to dependence on an underlying platform, ExternalResources can be used only
        in the init/post-init state, including the attempts to register custom resources. That is, resources cannot be
        managed from the __init__ methods of behavioral models, platforms, or services.

    """

    @abstractmethod
    def register_resource(self, scheme: str, resource: Union[Type, ResourceImpl]) -> bool:
        """
        Register a given resource for given scheme.

        :param scheme: URL scheme, i.e., the part before ://.
        :type scheme: str

        :param resource: The resource can either be provided as a type that implements the Resource and ResourceImpl
            interfaces, or it can be an object instance. If a type is provided then a new instance of the resource is
            created for each call of :func:`create_resource`, including the implicit call in sending and fetching
            function. If a resource instance is provided then this resource acts as a singleton and multiple interleaved
            :func:`open` and :func:`close` calls can happen and the resource must be prepared to handle it gracefully.
        :type resource: Union[Type, ResourceImpl]

        :return: True if the resource was successfully registered. False otherwise.
        """

    @abstractmethod
    def create_resource(self, path: str, params: Optional[dict[str, str]] = None, persistence: ResourcePersistence = ResourcePersistence.TRANSIENT) -> Resource:
        """
        Creates an instance of a resource with a given path.

        :param path: The URL of the resource. Full URL with scheme, e.g., file:// must be supplied to let system
            choose the correct one.
        :type path: str

        :param params: Arbitrary set of parameters that will be passed to the resource's init function. If the resource
            is a singleton (cf. :func:`register_resource`) then these parameters are ignored.
        :type params: Optional[dict[str, str]]

        :param persistence: The persistence of a resource. The :func:`create_resource` function is usually called
            implicitly from the other functions, which set the persistence to transient. However, if you do not want
            the resource to be created and destroyed after each call, set the persistence to
            ResourcePersistence.PERSISTENT.
        :type persistence: ResourcePersistence

        :return: An instance of a resource. Otherwise, an exception is thrown.
        """

    @abstractmethod
    def release_resource(self, resource: Resource) -> None:
        """
        Releases a persistent resource. For a transient resource, this is a no-operation.

        :param resource: An instance of a resource to close.
        :type resource: Resource

        :return: Nothing. This call always succeeds.
        """

    @abstractmethod
    async def send_async(self, resource: Union[str, Resource], data: str, params: Optional[dict[str, str]] = None, timeout: float = 0.0) -> int:
        """
        Asynchronously send data to a resource. This function is intended to be used by behavioral models and platforms.
        The agents currently must use the synchronous option.

        :param resource: Either an instance of a resource, or its URL. When the URL is used, the resource is
            automatically created and destroyed within the call.
        :type resource: Union[str, Resource]

        :param data: Any data will be written to the resource. Technically, this can be empty and the contents can
            depend on the params.
        :type data: str

        :param params: Parameters for the sending operation. Such as choosing the write or append mode for the file
            resource.
        :type params: Optional[dict[str, str]]

        :param timeout: A maximum time given for the operation to finish. The semantic differs for simulated and
            emulated environments. For simulated ones, the timeout represents the actual length in virtual time units,
            whereas for emulated ones, the timeout is the maximum time to finish. That is, simulated send will always
            take timeout number of time units, and emulated will take up-to timeout time units.
        :type timeout: float

        :return: The number of bytes written. However, the sending operation is expected to write all of its contents.
            In case of some error an exception should be thrown.
        """

    @abstractmethod
    def send(self, resource: Union[str, Resource], data: str, params: Optional[dict[str, str]] = None, timeout: float = 0.0, callback_service: Optional[ActiveService] = None) -> None:
        """
        Synchronously send data to a resource. This function is expected to be used by agents, but it can be with a
        bit of over-engineering used by behavioral models and platforms as well. The main difference is that the
        results of the send operation are send inside a :class:`MessageType.RESOURCE` message.

        :param resource: Either an instance of a resource, or its URL. When the URL is used, the resource is
            automatically created and destroyed within the call.
        :type resource: Union[str, Resource]

        :param data: Any data will be written to the resource. Technically, this can be empty and the contents can
            depend on the params.
        :type data: str

        :param params: Parameters for the sending operation. Such as choosing the write or append mode for the file
            resource.
        :type params: Optional[dict[str, str]]

        :param timeout: A maximum time given for the operation to finish. The semantic differs for simulated and
            emulated environments. For simulated ones, the timeout represents the actual length in virtual time units,
            whereas for emulated ones, the timeout is the maximum time to finish. That is, simulated send will always
            take timeout number of time units, and emulated will take up-to timeout time units.
        :type timeout: float

        :param callback_service: A reference to an active service that will receive the result of the call within
            a resource message.
        :type callback_service: Optional[ActiveService] = None

        :return: None. The sending operation is always expected to write all of its contents. In case of some error
            an exception is thrown.
        """

    @abstractmethod
    async def fetch_async(self, resource: Union[str, Resource], params: Optional[dict[str, str]] = None, timeout: float = 0.0) -> Optional[str]:
        """
        Asynchronously reads data from a resource. This function is intended to be used by behavioral models and
        platforms. The agents currently must use the synchronous option.

        :param resource: Either an instance of a resource, or its URL. When the URL is used, the resource is
            automatically created and destroyed within the call.
        :type resource: Union[str, Resource]

        :param params: Parameters for the receiving operation.
        :type params: Optional[dict[str, str]]

        :param timeout: A maximum time given for the operation to finish. The semantic differs for simulated and
            emulated environments. For simulated ones, the timeout represents the actual length in virtual time units,
            whereas for emulated ones, the timeout is the maximum time to finish. That is, simulated send will always
            take timeout number of time units, and emulated will take up-to timeout time units.
        :type timeout: float

        :return: The data read from the resource. It may return none and still be correct, such as the HEAD HTML
            request.
        """

    @abstractmethod
    def fetch(self, resource: Union[str, Resource], params: Optional[dict[str, str]] = None, timeout: float = 0.0, callback_service: Optional[ActiveService] = None) -> None:
        """
        Synchronously reads data from a resource. This function is expected to be used by agents, but it can be with a
        bit of over-engineering used by behavioral models and platforms as well. The main difference is that the
        results of the fetch operation are send inside a :class:`MessageType.RESOURCE` message.

        :param resource: Either an instance of a resource, or its URL. When the URL is used, the resource is
            automatically created and destroyed within the call.
        :type resource: Union[str, Resource]

        :param params: Parameters for the receiving operation.
        :type params: Optional[dict[str, str]]

        :param timeout: A maximum time given for the operation to finish. The semantic differs for simulated and
            emulated environments. For simulated ones, the timeout represents the actual length in virtual time units,
            whereas for emulated ones, the timeout is the maximum time to finish. That is, simulated send will always
            take timeout number of time units, and emulated will take up-to timeout time units.
        :type timeout: float

        :param callback_service: A reference to an active service that will receive the result of the call within
            a resource message.
        :type callback_service: Optional[ActiveService] = None

        :return: The data read from the resource. It may return none and still be correct, such as the HEAD HTML
            request.
        """
