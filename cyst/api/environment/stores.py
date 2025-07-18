from abc import ABC, abstractmethod
from dataclasses import dataclass
from deprecated.sphinx import versionchanged, versionadded
from typing import List, Optional, Tuple, Union, Dict, Any, Callable

from cyst.api.environment.data_model import ActionModel
from cyst.api.environment.message import Message, Signal
from cyst.api.environment.stats import Statistics
from cyst.api.host.service import ActiveService
from cyst.api.logic.access import AccessLevel
from cyst.api.logic.action import Action, ActionDescription
from cyst.api.logic.exploit import Exploit, ExploitCategory
from cyst.api.network.node import Node


class ActionStore(ABC):
    """
    Action store provides access to actions that are available to services.
    """

    @abstractmethod
    def get(self, id: str = "") -> Optional[Action]:
        """
        Returns an action with given ID. This function makes a copy of the object, which is present in the store. This
        is a preferred variant, because any parameters set on that action would propagate to the store.

        :param id: A unique ID of the action.
        :type id: str

        :return: An action, if there is one with such ID and for such execution environment.
        """

    @abstractmethod
    def get_ref(self, id: str = "") -> Optional[Action]:
        """
        Return an action with give ID. This function returns a reference to the object stored in the store and any
        parameter alterations will propagate to all subsequent queries for this action.

        :param id: A unique ID of the action.
        :type id: str

        :return: An action, if there is one with such ID and for such execution environment.
        """

    @abstractmethod
    def get_prefixed(self, prefix: str = "") -> List[Action]:
        """
        Gets a list of actions, whose ID starts with a given string. This is usually done to get access to the entire
        namespace of a particular behavioral model.

        The list will contain copies of actions present in the store. Getting multiple references in one call is not
        supported.

        :param prefix: The prefix all actions IDs must share.
        :type prefix: str

        :return: A list of actions with the same prefix.
        """

    @abstractmethod
    def add(self, action: ActionDescription) -> None:
        """
        Adds a new action to the store. This function should be used in two cases:

        * Adding new action for a behavioral model. Such action must have a processing function mapped to the
          action ID.

        * Adding new action for intra-agent communication. There is no requirement on the action form, however
          an exception will be thrown, if this action is directed to a passive service, as the system will have
          no idea how to process it.

        :param action: A description of the action to add.
        :type action: ActionDescription

        :return: None
        """


class ExploitStore(ABC):
    """
    Exploit store provides access to exploits that can be used together with actions. Unlike the action store,
    runtime definition of exploits by services is not permitted. This must be done through the
    :class:`cyst.api.environment.configuration.ExploitConfiguration` interface.
    """

    @abstractmethod
    def get_exploit(self, id: str = "", service: str = "", category: ExploitCategory = ExploitCategory.NONE) -> Optional[List[Exploit]]:
        """
        Gets an exploit, which satisfy all the parameters.

        :param id: An explicit ID of an exploit.
        :type id: str

        :param service: An ID of a service the exploit can be used at.
        :type service: str

        :param category: A category that the exploit should have. If the ExploitCategory.NONE is set, then the category
            is not considered when retrieving the exploits.
        :type category: ExploitCategory

        :return: A list of exploits satisfying the parameters.
        """

    @abstractmethod
    def evaluate_exploit(self, exploit: Union[str, Exploit], message: Message, node: Node) -> Tuple[bool, str]:
        """
        Evaluates, whether the provided exploit is applicable, given the message which carries the relevant action and
        a concrete node. TODO: This interface is cumbersome. While this is best fit for the data that interpreters
        receive, it is confusing at best.

        :param exploit: The ID of the exploit or its instance.
        :type exploit: Union[str, Exploit]

        :param message: An instance of the message which carried the exploit.
        :type message: Message

        :param node: An instance of the node, where the exploit is being applied.
        :type node: Node

        :return: (True, _) if exploit is applicable, (False, reason) otherwise.
        """


@versionadded(version="0.6.0")
class ServiceStore(ABC):
    """
    Service store provides a unified interface for creating active services. Due to centrality of this concept to all
    CYST, regardless of the platform it uses, all services must be instantiated through this store.
    """

    @abstractmethod
    def create_active_service(self, type: str, owner: str, name: str, node: Node,
                              service_access_level: AccessLevel = AccessLevel.LIMITED,
                              configuration: Optional[Dict[str, Any]] = None, id: str = "") -> Optional[ActiveService]:
        """
        Creates an active service instance.

        :param type: The name of the active service, under which it is registered into the system.
        :param owner: The identity of user, under whose identity this service should be running.
        :param name: The name of the service, under which it is present at the node. Currently, it is used instead
            of ports to route messages. TODO: The name/id system is retarded and has to be changed.
        :param node: The node at which the service should be instantiated.
        :param service_access_level: The level of access the service has on the system.
        :param id: System-wide unique ID of the service. Unless overridden, it will have the form of
            `<node_id>.<service_name>`.
        :param configuration: A dictionary with arbitrary configuration items.

        :return: The instantiated active service or None if there was an error.
        """

    @abstractmethod
    def get_active_service(self, id) -> Optional[ActiveService]:
        """
        Returns an already instantiated active service, given its full id (that is, not just a name).

        :param id:
        :return:
        """


@versionadded(version="0.6.0")
class DataStore(ABC):

    @abstractmethod
    def add_action(self, action: ActionModel) -> None:
        """
        Store information about a resolved action, i.e., after completing the request-response cycle.

        :param action: An action description

        :return: None
        """

    @abstractmethod
    def add_message(self, message: Message) -> None:
        """
        Store information about a message. While in general, the message information is available only at the point of
        dispatching the message, platforms that have more control over the message passing process (e.g., simulation
        platform of CYST) may report the same message multiple times during the message passing. Additional information
        shall then be passed through the .platform_specific attributed, which gets erased before entering user-facing
        side of the code.

        :param message: The message to store

        :return: None
        """

    @abstractmethod
    def add_statistics(self, statistics: Statistics) -> None:
        """
        Store statistics related to one run.

        :param statistics: The statistics to store.

        :return: None
        """

    @abstractmethod
    def add_signal(self, signal: Signal) -> None:
        """
        Store a signal.

        :param signal: THe signal to store.

        :return: None
        """


@versionadded(version="0.6.0")
@dataclass
class DataStoreDescription:
    """
    Entry point for an implementation of a data store backend.

    :param backend: The name of the backend the data store uses. This name has to be unique within the system.
    :type backend: str

    :param description: A textual description of the data store backend.
    :type description: str

    :param creation_fn: A factory function that can create the data store backend. Its parameters are the run_id and
        backend-specific key-value pairs.
    :type creation_fn: Callable[[str, Dict[str, str]], DataStore]
    """
    backend: str
    description: str
    creation_fn: Callable[[str, Dict[str, str]], DataStore]
