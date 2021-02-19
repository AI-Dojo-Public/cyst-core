from abc import ABC, abstractmethod

from typing import List, Tuple, Union, Optional

from cyst.api.host.service import Service
from cyst.api.logic.access import AccessLevel, Authorization
from cyst.api.network.node import Node


class EnvironmentPolicy(ABC):

    @abstractmethod
    def create_authorization(self, identity: str, nodes: List[Union[str, Node]], services: List[Union[str, Service]], access_level: AccessLevel, id: Optional[str] = None, token: Optional[str] = None) -> Authorization:
        pass

    @abstractmethod
    def create_stub_authorization(self, identity: Optional[str] = None, nodes: Optional[List[Union[str, Node]]] = None, services: Optional[List[Union[str, Service]]] = None, access_level: AccessLevel = AccessLevel.NONE) -> Authorization:
        pass

    @abstractmethod
    def create_stub_from_authorization(self, authorization: Authorization) -> Authorization:
        pass

    @abstractmethod
    def add_authorization(self, *authorizations: Authorization) -> None:
        pass

    @abstractmethod
    def get_authorizations(self, node: Union[str, Node], service: str, access_level: AccessLevel = AccessLevel.NONE) -> List[Authorization]:
        pass

    @abstractmethod
    def decide(self, node: Union[str, Node], service: str, access_level: AccessLevel, authorization: Authorization) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def get_nodes(self, authorization: Authorization) -> List[str]:
        pass

    @abstractmethod
    def get_services(self, authorization: Authorization) -> List[str]:
        pass

    @abstractmethod
    def get_access_level(self, authorization: Authorization) -> AccessLevel:
        pass
