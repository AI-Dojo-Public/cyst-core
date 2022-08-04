from abc import ABC, abstractmethod

from typing import List, Tuple, Union, Optional

from cyst.api.host.service import Service
from cyst.api.logic.access import AccessLevel, AccessScheme, Authorization
from cyst.api.network.node import Node


class EnvironmentPolicy(ABC):
    """
    This environment enables handling of authentication and authorization.

    Warning:
        This interface will be gradually phased off in favor of a new auth framework.
    """

    @abstractmethod
    def create_authorization(self, identity: str, nodes: List[Union[str, Node]], services: List[Union[str, Service]],
                             access_level: AccessLevel, id: str, token: Optional[str] = None) -> Authorization:
        """
        Creates an authorization token, which can be used to get access to service resources.

        :param identity: An identity of a user this token belongs to. Usually the identity of a resource and the
            identity of a token must match to get authorized.
        :type identity: str

        :param nodes: A list of nodes this authorization token can be used on. Either a node instance or a node ID
            can be used.
        :type nodes: List[Union[str, Node]]

        :param services: A list of services this authorization token can be used on. Either a service instance or a
            service ID can be used.
        :type services: List[Union[str, Service]]

        :param access_level: The access level of the service.
        :type access_level: AccessLevel

        :param id: An ID of the authorization token. This ID has to be unique across simulation to enable correct
            evaluation of access rights.
        :type id: str

        :param token: An optional data payload related to the authorization token. Mostly useless now, as the payload
            is more important for authentication token, that were established within the new auth framework.
        :type token: Optional[str]

        :return: An authorization token
        """
        pass

    @abstractmethod
    def get_authorizations(self, node: Union[str, Node], service: str, access_level: AccessLevel = AccessLevel.NONE) -> List[Authorization]:
        """
        Gets authorization templates for a given service on a given node with a specified access level. Note that these
        are _templates_ and not actual authorizations. For more information, see description of the auth framework.

        :param node: An instance or an ID of the node.
        :type node: Union[str, Node]

        :param service: A name of the service.
        :type service: str

        :param access_level: An access level that the authorization should have.
        :type access_level: AccessLevel

        :return: A list of authorization templates.
        """
        pass

    @abstractmethod
    def decide(self, node: Union[str, Node], service: str, access_level: AccessLevel, authorization: Authorization) -> Tuple[bool, str]:
        """
        Evaluates, whether an authorization is applicable for a given service, on a given node and with given
        access level.

        :param node: An instance or an ID of the node.
        :type node: Union[str, Node]

        :param service: A name of the service.
        :type service: str

        :param access_level: An access level that the authorization should have.
        :type access_level: AccessLevel

        :param authorization: The authorization that is being tested.
        :type authorization: Authorization

        :return: An information if the authorization is applicable and if not, also the reason why.

            :Applicable authorization: (True, "")
            :Wrong authorization: (False, "Reason")

        """
        pass

    @abstractmethod
    def get_schemas(self, node: Union[str, Node], service: str) -> List[AccessScheme]:
        """
        schemas under which the service is accessible
        TODO
        """
        pass

    @abstractmethod
    def get_nodes(self, authorization: Authorization) -> List[str]:
        """
        Gets the IDs of nodes that this authorization pertain to. This function exists, because the nodes list is not
        accessible via the :class:`cyst.api.logic.access.Authorization` interface.

        :param authorization: An instance of the authorization.
        :type authorization: Authorization
        """
        pass

    @abstractmethod
    def get_services(self, authorization: Authorization) -> List[str]:
        """
        Gets the IDs of services that this authorization pertain to. This function exists, because the services list is
        not  accessible via the :class:`cyst.api.logic.access.Authorization` interface.

        :param authorization: An instance of the authorization.
        :type authorization: Authorization
        """
        pass

    @abstractmethod
    def get_access_level(self, authorization: Authorization) -> AccessLevel:
        """
        Gets the access level of the authorization. TODO: I have no idea, why this function exists, because access level
        is accessible via the Authorization interface.

        :param authorization: An instance of the authorization.
        :type authorization: Authorization
        """
        pass
