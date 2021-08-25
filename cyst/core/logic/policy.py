from typing import List, Union, Optional, Tuple

from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.host.service import Service
from cyst.api.logic.access import AccessLevel, Authorization
from cyst.api.network.node import Node
from cyst.core.host.service import PassiveServiceImpl
from cyst.core.logic.access import AuthorizationImpl
from cyst.core.network.node import NodeImpl


class Policy(EnvironmentPolicy):

    def __init__(self, configuration: EnvironmentConfiguration):
        self._config = configuration

    def create_authorization(self, identity: str, nodes: List[Union[str, Node]], services: List[Union[str, Service]],
                             access_level: AccessLevel, id: Optional[str] = None,
                             token: Optional[str] = None) -> Optional[Authorization]:

        if not nodes or not services:
            return None

        auth = AuthorizationImpl(identity, nodes, services, access_level, id, token)

        if len(nodes) > 1 or services == ["*"]: # federated, temporary solution
            return auth

        actual_node = nodes[0] if isinstance(nodes[0], Node) else self._config.general.get_object_by_id(nodes[0], Node)
        # if nodes is a [str], is it id, ip or else??

        for service in services:
            actual_service = service if isinstance(service, Service)\
                else actual_node.services.get(service)
            if isinstance(actual_service, PassiveServiceImpl):
                actual_service.add_active_authorization(auth)

        return auth



    def create_stub_authorization(self, identity: Optional[str] = None, nodes: Optional[List[Union[str, Node]]] = None,
                                  services: Optional[List[Union[str, Service]]] = None,
                                  access_level: AccessLevel = AccessLevel.NONE) -> Authorization:
        pass

    def create_stub_from_authorization(self, authorization: Authorization) -> Authorization:
        pass

    def add_authorization(self, *authorizations: Authorization) -> None:
        pass

    def get_authorizations(self, node: Union[str, Node], service: str, access_level: AccessLevel = AccessLevel.NONE) -> \
    List[Authorization]:
        pass

    def decide(self, node: Union[str, Node], service: str, access_level: AccessLevel, authorization: Authorization) -> \
    Tuple[bool, str]:

        actual_node = node if isinstance(node, Node) else self._config.general.get_object_by_id(node, Node)

        actual_service = actual_node.services.get(service)

        if not actual_service:
            return False, "Service does not exist on node."

        retval = None

        if isinstance(actual_service, PassiveServiceImpl):
            retval = actual_service.assess_authorization(authorization, access_level,
                                                         NodeImpl.cast_from(actual_node).id, service)

        if not retval:
            return False, "Invalid service type."

        return retval




    def get_nodes(self, authorization: Authorization) -> List[str]:
        return AuthorizationImpl.cast_from(authorization).nodes

    def get_services(self, authorization: Authorization) -> List[str]:
        return AuthorizationImpl.cast_from(authorization).services

    def get_access_level(self, authorization: Authorization) -> AccessLevel:
        return AuthorizationImpl.cast_from(authorization).access_level