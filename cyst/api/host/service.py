from abc import ABC, abstractmethod
from dataclasses import dataclass
from deprecated.sphinx import versionchanged
from enum import IntEnum
from semver import VersionInfo
from typing import Set, Tuple, Callable, Dict, Any, Optional

from cyst.api.environment.message import Message
from cyst.api.logic.access import AccessLevel
from cyst.api.utils.tag import Tag


class Service(ABC):
    """
    Service represents an abstraction of any notable process that is running on a node. Services exist in two flavors:
    passive and active. Active services can initiate request-response exchange and manage their own response processing.
    Passive services exist only as a descriptions of their properties and their responses are evaluated by the
    environment.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the service. This name is unique within a node and serves as a destination name for messages.

        :rtype: str
        """

    @property
    @abstractmethod
    def owner(self) -> str:
        """
        The identity of the owner of the service.

        :rtype: str
        """

    @property
    @abstractmethod
    def service_access_level(self) -> AccessLevel:
        """
        The access level with which the service can access resources of the node.

        :rtype: AccessLevel
        """

    @property
    @versionchanged(version="0.6.0", reason="Changed to return Optional ")
    @abstractmethod
    def passive_service(self) -> Optional['PassiveService']:
        """
        If the service is a passive one, this function gives access to its :class:`PassiveService` interface.

        :rtype: Optional[PassiveService]
        """

    @property
    @versionchanged(version="0.6.0", reason="Changed to return Optional ")
    @abstractmethod
    def active_service(self) -> Optional['ActiveService']:
        """
        If the service is an active one, this function gives access to its :class:`ActiveService` interface.

        :rtype: Optional[ActiveService]
        """


class ActiveService(ABC):
    """
    Active service is used to model any active actor within the simulation. Every agent that is being run in the
    simulation must implement this interface.
    """

    @abstractmethod
    def run(self) -> None:
        """
        Starts the service. This function si automatically called by the environment at the initialization.
        """

    @abstractmethod
    def process_message(self, message: Message) -> Tuple[bool, int]:
        """
        This function is called by the environment whenever a message arrives at the service.

        :param message: The message to process.
        :type message: Message

        :return: A tuple indicating, whether the processing was successful and eventually, how long the processing took.
            Depending on the role of the service, this return value results in different outcomes. For traffic,
            processors, i.e., services that process messages before they arrive into their final destination, returning
            (False, _) results in dropping of the message at that point. After returning (True, _) the messages is
            passed further. For destination services the resulting value currently does not play a role. Both types of
            services are expected to create and send an appropriate response. TODO: This should have the same result
            as the behavioral models and return a Response. That way, there can be a failsafe built-in.
        :rtype: Tuple[bool, int]
        """


@dataclass
class ActiveServiceDescription:
    """
    This is a description of an active service. It is used to register a new active service into the system.

    :param name: A name of the active service. It has to be unique among other registered services.
    :type name: str

    :param description: A short description of the service purpose and function.
    :type description: str

    :param creation_fn: A function that is able to create instances of the service.
    :type creation_fn: Callable[[EnvironmentMessaging, EnvironmentResources, Optional[Dict[str, Any]]], ActiveService]
    """

    name: str
    description: str
    # TODO services are currently called with Dict[str, Any] for configuration. In the future, they should provide some
    #      information about their configuration
    creation_fn: Callable[['cyst.api.environment.messaging.EnvironmentMessaging',
                           'cyst.api.environment.resources.EnvironmentResources',
                           Optional[Dict[str, Any]]], ActiveService]


class ServiceState(IntEnum):
    """
    Service state represents the state of a service.

    Possible values:
        :INIT: A state that used when service is created and before environment was started.
        :RUNNING: A default state that is set when the environment has started.
        :PAUSED: A state in which service can't be accessed, but can be reactivated.
        :ZOMBIE: A state in which service can't be accessed and can't be reactivated.
    """
    INIT = 0
    RUNNING = 1
    PAUSED = 2
    ZOMBIE = 3


class PassiveService(Service, ABC):
    """
    Passive service is used to model an arbitrary service running on a node, which only passively reacts to the actions
    by other actors within a simulation.
    """

    @property
    @abstractmethod
    def version(self) -> VersionInfo:
        """
        The version of the service.

        :rtype: VersionInfo
        """

    @property
    @abstractmethod
    def state(self) -> ServiceState:
        """
        The state of the service.

        :rtype: ServiceState
        """

    @property
    @abstractmethod
    def tags(self) -> Set[Tag]:
        """
        Set of tags describing the service. It should provide high-level specification of service purpose. In the
        future, we expect to have a complete domain of services, from which the tags could be chosen. This will also
        be beneficial for automated generation of simulation scenarios.

        :rtype: Set[Tag]
        """

    @property
    @abstractmethod
    def enable_session(self) -> bool:
        """
        Returns, whether the service enables creation of sessions.

        :rtype: bool
        """

    @property
    @abstractmethod
    def session_access_level(self) -> AccessLevel:
        """
        Returns an access level of eventual sessions. This can be different from the access level of the service itself.
        For example ssh has elevated access level, but its sessions only have user level access.

        :rtype: AccessLevel
        """

    @property
    @abstractmethod
    def local(self) -> bool:
        """
        Returns whether the service is accessible from the network, or if the only way to address it is from the same
        node.

        :rtype: bool
        """
