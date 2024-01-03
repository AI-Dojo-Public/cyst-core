from abc import ABC, abstractmethod
from dataclasses import dataclass
from deprecated.sphinx import versionchanged
from typing import Callable

from cyst.api.environment.configuration import ActionConfiguration
from cyst.api.environment.stores import ActionStore
from cyst.api.environment.message import Message
from cyst.api.logic.action import Action
from cyst.api.logic.metadata import Metadata


class MetadataProvider(ABC):
    """
    Metadata providers supply messages with additional information that are meant to mimic observations that can be
    done in the real life. Two typical examples of metadata can be 1) flow information, 2) results of traffic analyses.
    """
    @versionchanged(version="0.6.0", reason="Metadata are collected for a whole message at the time of sending and are no longer solely dependent on Action.")
    @abstractmethod
    def get_metadata(self, action: Action, message: Message) -> Metadata:
        """
        This function should return metadata that correspond to the given message.

        :param action: The action for which the metadata should be provided. Given that a message can carry multiple
            actions, a metadata provider must adhere to this parameter and not try to extract it from the message
            itself.
        :type action: Action

        :param message: An instance of the message. The message should be used to provide additional information
            necessary to supply correct metadata, such as message type, message status, etc.
        :type message: Message

        :return: A metadata associated with the message.
        """
        pass


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
    creation_fn: Callable[[], MetadataProvider]
