from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from cyst.api.environment.configuration import ActionConfiguration
from cyst.api.environment.stores import ActionStore
from cyst.api.logic.action import Action
from cyst.api.logic.metadata import Metadata


class MetadataProvider(ABC):
    """
    Metadata providers supply messages with additional information that are meant to mimic observations that can be
    done in the real life. Two typical examples of metadata can be 1) flow information, 2) results of traffic analyses.
    """
    @abstractmethod
    def register_action_parameters(self) -> None:
        """
        There can be classes of metadata that are different for a particular action with particular parameters as
        defined by the behavioral model. These different classes can manifest depending on parameters that are not
        considered in the model itself. An example of such difference are various scanning techniques for a
        reconnaissance action (e.g., SYN, FIN, XMAS scans). Each of these techniques would have different statistical
        properties that would reflect in, e.g., flow information.

        This function gives the metadata providers an option to inject its own parameters into the actions of the action
        store. These parameters should have a closed parameter domain for this to be reasonably usable.
        Considering that this inject is done on a per-action basis, the metadata provider must understand the
        semantic of specific actions, so it is expected that such providers are released together with behavioral
        model implementation.
        """

    @abstractmethod
    def get_metadata(self, action: Action) -> Metadata:
        """
        This function should return metadata that correspond to the given action and its parameters.

        :param action: An instance of the action.
        :type action: Action

        :return: A metadata associated with the action.
        """


@dataclass
class MetadataProviderDescription:
    """ A description of a metadata provider which should be registered into the system.

    :param namespace: A namespace of actions that this provider works with.
    :type namespace: str

    :param description: A short description of the provider.
    :type description: str

    :param creation_fn: A factory function that creates instances of the metadata provider.
    :type creation_fn: Callable[[ActionStore, ActionConfiguration], MetadataProvider]
    """
    namespace: str
    description: str
    creation_fn: Callable[[ActionStore, ActionConfiguration], MetadataProvider]
