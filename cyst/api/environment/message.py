from abc import ABC, abstractmethod
from dataclasses import dataclass
from deprecated.sphinx import versionadded
from enum import Enum, auto
from netaddr import IPAddress
from typing import Any, Optional, Union, TypeVar, Type, Dict

from cyst.api.network.session import Session
from cyst.api.logic.access import Authorization, AuthenticationToken, AuthenticationTarget
from cyst.api.logic.action import Action
from cyst.api.logic.metadata import Metadata


class MessageType(Enum):
    """ The type of the message.

    Possible values:

        :TIMEOUT: The message is an information about expiration of a timeout.
        :REQUEST: The message is a request.
        :RESPONSE: The message is a response.
        :RESOURCE: The message carries a resource.

    """
    TIMEOUT = 0
    REQUEST = 1
    RESPONSE = 2
    RESOURCE = 3


class StatusOrigin(Enum):
    """ Indicates the origin of the status of the response.

    Possible values:

        :NETWORK: The original request was processed and evaluated at the network or router level.
        :NODE: The original request was processed and evaluated at the node level, without reaching a specific service.
        :SERVICE: The original request was processed and evaluated at the service level.
        :RESOURCE: The original request was for the resources.
        :SYSTEM: The original request couldn't be evaluated in the environment context. This indicates a system error.

    """
    NETWORK = 0
    NODE = 1
    SERVICE = 2
    RESOURCE = 3
    SYSTEM = 99


class StatusValue(Enum):
    """ Indicates the general result of the response.

    Possible values:

        :SUCCESS: The action intended in the original request was successfully carried out.
        :FAILURE: The action intended in the original request was not successful due to wrong parameter combination or
            values.
        :ERROR: The action intended in the original request was not successful because of missing parameters or because
            the action could not be evaluated.
        :PARTIAL: The action intended in the original request was partially successful and another response should be
            expected to arrive soon.

    """
    SUCCESS = 0
    FAILURE = 1
    ERROR = 2
    PARTIAL = 3


class StatusDetail(Enum):
    """ Status detail provides another introspection mechanism to active services into the nature of failures and
    errors. Status detail follows unified naming convention WHAT_WHY, where WHY is one of the following:

    * NOT_PROVIDED: WHAT was not passed as a parameter, even though it is required

    * NOT_EXISTING: WHAT does not exist within the context of current simulation run (e.g., service name, user name,
      etc.)

    * NOT_APPLICABLE: WHAT cannot be used (e.g., wrong authorization, wrong exploit parameters, etc.)

    * NOT_SUPPORTED: WHAT exists as a valid concept, but the target does not support it (e.g., attempting to open a
      session to a service that does not support it)

    * NEXT: WHAT was a correct step towards success, but another WHAT is required

    General:
        :UNKNOWN: There is no additional detail to be provided.

    NODE.FAILURE:
        :PRIVILEGES_NOT_APPLICABLE: A wrong authentication/authorization used.

    NODE.ERROR:
        :SERVICE_NOT_PROVIDED: No service was specified.
        :SERVICE_NOT_EXISTING: A service does not exist at the node.
        :SESSION_NOT_PROVIDED: A session was required but not provided.
        :SESSION_NOT_APPLICABLE: A wrong session was provided.

    SERVICE.FAILURE:
        :SESSION_CREATION_NOT_SUPPORTED: A session cannot be created with this service.
        :EXPLOIT_NOT_PROVIDED: An action required an exploit, but it was not provided.
        :EXPLOIT_NOT_APPLICABLE: An exploit could not be used in combination with an action to affect the service.
        :EXPLOIT_CATEGORY_NOT_APPLICABLE: Wrong exploit category was used (e.g., data manipulation exploit for privilege
            escalation)
        :EXPLOIT_LOCALITY_NOT_APPLICABLE: Wrong exploit locality was used (e.g., local exploit for remote action)
        :EXPLOIT_PARAMETER_NOT_PROVIDED: A required exploit parameter was missing.
        :EXPLOIT_PARAMETER_NOT_APPLICABLE: A provided parameter in exploit could not be used to affect the service.
        :AUTHORIZATION_NOT_PROVIDED: An authorization was missing when trying to access the service.
        :AUTHORIZATION_NOT_APPLICABLE: A wrong authorization was used to access the service.
        :AUTHENTICATION_NOT_PROVIDED: An authentication token was missing when trying to authenticate against the
            service.
        :AUTHENTICATION_NOT_APPLICABLE: A wrong authentication token was used when trying to authenticate against the
            service.
        :AUTHENTICATION_NEXT: A previous step in multi-factor authentication step was successful, another step must
            be undertaken.

    SYSTEM.ERROR:
        :ACTION_NOT_EXISTING: There is no interpreter able to interpret the given action.

    """
    UNKNOWN = 0
    # NODE.FAILURE
    PRIVILEGES_NOT_APPLICABLE = auto()

    # NODE.ERROR
    SERVICE_NOT_PROVIDED = auto()
    SERVICE_NOT_EXISTING = auto()
    SESSION_NOT_PROVIDED = auto()
    SESSION_NOT_APPLICABLE = auto()

    # SERVICE.FAILURE
    SESSION_CREATION_NOT_SUPPORTED = auto()
    EXPLOIT_NOT_PROVIDED = auto()
    EXPLOIT_NOT_APPLICABLE = auto()
    EXPLOIT_CATEGORY_NOT_APPLICABLE = auto()
    EXPLOIT_LOCALITY_NOT_APPLICABLE = auto()
    EXPLOIT_PARAMETER_NOT_PROVIDED = auto()
    EXPLOIT_PARAMETER_NOT_APPLICABLE = auto()
    AUTHORIZATION_NOT_PROVIDED = auto()
    AUTHORIZATION_NOT_APPLICABLE = auto()
    AUTHENTICATION_NOT_PROVIDED = auto()
    AUTHENTICATION_NOT_APPLICABLE = auto()
    AUTHENTICATION_NEXT = auto()

    # SERVICE.ERROR

    # SYSTEM.FAILURE

    # SYSTEM.ERROR
    ACTION_NOT_EXISTING = auto()


@dataclass
class Status:
    """ Status is bound to responses, as it informs about the result of request processing.

    :param origin: The origin of the status.
    :type origin: StatusOrigin

    :param value: The value of the status.
    :type value: StatusValue

    :param detail: Additional specification of the status value.
    :type detail: StatusDetail
    """
    origin: StatusOrigin
    value: StatusValue
    detail: StatusDetail = StatusDetail.UNKNOWN

    def __str__(self) -> str:
        if self.detail != StatusDetail.UNKNOWN:
            result = "({}, {}, {})".format(self.origin.name, self.value.name, self.detail.name)
        else:
            result = "({}, {})".format(self.origin.name, self.value.name, self.detail.name) #MYPY: Missing one {} or one too many items
        return result


T = TypeVar('T', bound=Union['Request', 'Response', 'Resource', 'Timeout'])


class Message(ABC):
    """
    Message provides a mean to exchange information between elements of the simulation.
    """

    @property
    @abstractmethod
    def id(self) -> int:
        """
        A numerical identifier of the message, which is unique across a simulation run. The request and response share
        the same id to enable correct pairing.

        :rtype: int
        """

    @property
    @abstractmethod
    def type(self) -> MessageType:
        """
        A type of the message.

        :rtype: MessageType
        """

    @property
    @abstractmethod
    def src_ip(self) -> Optional[IPAddress]:
        """
        An IP address from which the message was sent. Messages not yet sent and timeouts do not have a source IP.

        :rtype: Optional[IPAddress]
        """

    @property
    @abstractmethod
    def dst_ip(self) -> Optional[IPAddress]:
        """
        An IP address where the message was sent to. Timeouts do not have a destination IP.

        :rtype: Optional[IPAddress]
        """

    @property
    @abstractmethod
    def src_service(self) -> Optional[str]:
        """
        A service that produced the message. In case of service-less origins, such as router processing, the service
        is empty.

        :rtype: Optional[str]
        """

    @property
    @abstractmethod
    def dst_service(self) -> str:
        """
        A service that is the ultimate target for the message.

        :rtype: str
        """

    @property
    @abstractmethod
    def session(self) -> Optional[Session]:
        """
        A session associated with the message.

        :rtype: Session
        """

    @property
    @abstractmethod
    def auth(self) -> Optional[Union[Authorization, AuthenticationToken, AuthenticationTarget]]:
        """
        An authentication/authorization associated with the message. In case of requests, it can either contain
        Authorizations or Authentication tokens provided by the origin. In case of responses, it can be the original
        Authorization provided by the origin, Authorization provided by the destination service as a result of an
        actions, or Authentication target if the request was a part of multi-factor authentication scheme message
        exchange.

        :rtype: Optional[Union[Authorization, AuthenticationToken, AuthenticationTarget]]
        """

    @property
    @abstractmethod
    def ttl(self) -> int:
        """
        Time-to-live of the message. After each pass through a router, this value gets decreased and the message gets
        discarded if it ever reaches 0. This mechanism exists to prevent endless resending of a message in case of bad
        network topology.

        :rtype: int
        """

    @property
    @abstractmethod
    def metadata(self) -> Metadata:
        """
        Metadata associated with the message. The metadata is supplied to the message by metadata providers (see
        :class:`cyst.api.environment.metadata_provider.MetadataProvider`). The metadata mechanism is intended to
        provide at least some information for active services, who are not able to see the action portion of a
        message (at least that is the plan, currently they can).

        :rtype: Metadata
        """

    @abstractmethod
    def set_metadata(self, metadata: Metadata) -> None:
        """
        Sets a metadata to the message. This call overwrites the original value, so, if there is a multitude of
        metadata providers, it is advisable to use :func:`add_metadata()`.

        :param metadata: A new value of the metadata.
        :type metdata: Metadata
        """

    @versionadded(version="0.6.0")
    @property
    @abstractmethod
    def platform_specific(self) -> Dict[str, Any]:
        """
        Provides access to platform-specific parameters of a message. Their contents can be arbitrary and are intended
        for assisting with message handling in a non CYST-simulated environments.

        :rtype: Dict[str, Any]
        """

    @abstractmethod
    def cast_to(self, type: Type[T]) -> T:
        """
        This function enables typecasting of Message into one of the four derived types: Request, Response, Resource,
        and Timeout. While technically not necessary due to Python's type system, it conveys intention and also makes
        a check whether the conversion can actually be done.

        :param type: A type to cast the mesasge to.
        :type type: Type[TypeVar('T', bound=Union['Request', 'Response', 'Resource', 'Timeout'])]

        :rtype: T
        """


class Request(Message, ABC):
    """
    Request is a message specialization that carries an action.
    """

    @property
    @abstractmethod
    def action(self) -> Action:
        """
        Gets an action associated with the request.

        :rtype: Action
        """


class Response(Message, ABC):
    """
    Response is a message specialization the carries the result of associated request.
    """

    @versionadded(version="0.6.0")
    @property
    @abstractmethod
    def action(self) -> Action:
        """
        Gets an action associated with the original request.

        :rtype: Action
        """
        pass

    @property
    @abstractmethod
    def status(self) -> Status:
        """
        A result of processing the associated request.

        :rtype: Status
        """

    @property
    @abstractmethod
    def content(self) -> Optional[Any]:
        """
        Any associated information that was included during the processing of the associated request.

        :rtype: Optional[Any]
        """


class Timeout(Message, ABC):
    """
    Timeout is a message specialization that is delivered when a timeout requested through the
    :class:`cyst.api.environment.clock.Clock` interface.
    """
    @property
    @abstractmethod
    def start_time(self) -> int:
        """
        A simulation time when the timeout was requested.

        :rtype: int
        """

    @property
    @abstractmethod
    def duration(self) -> int:
        """
        A duration of the timeout in simulated time units.

        :rtype: int
        """

    @property
    @abstractmethod
    def parameter(self) -> Any:
        """
        Any parameter that was included during the invocation of the timeout function.

        :rtype: Any
        """


class Resource(Message, ABC):
    """
    Resource is a message specialization that is delivered when an asynchronous external resource was requested.
    """
    @property
    @abstractmethod
    def path(self) -> str:
        """
        A URL of the resource.

        :rtype str:
        """

    @property
    @abstractmethod
    def status(self) -> Status:
        """
        A result of processing the associated request.

        :rtype: Status
        """


    @property
    @abstractmethod
    def data(self) -> Optional[str]:
        """
        Data retrieved from the external resource. In case the system failed to extract the data (due to timeout or
        error), the return is set to None.

        :rtype: Optional[str]
        """
