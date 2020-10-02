from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union, Dict, TypeVar, Type
from netaddr import IPAddress
from flags import Flags

from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.message import Message
from cyst.api.host.service import Service, PassiveService, ActiveService
from cyst.api.logic.access import Authorization, AccessLevel
from cyst.api.logic.data import Data
from cyst.api.logic.exploit import VulnerableService, ExploitCategory, ExploitLocality, ExploitParameter, ExploitParameterType, Exploit
from cyst.api.network.elements import Connection, Interface, Route
from cyst.api.network.firewall import FirewallRule, FirewallPolicy
from cyst.api.network.session import Session
from cyst.api.network.node import Node


ActiveServiceInterfaceType = TypeVar('ActiveServiceInterfaceType')


class NodeConfiguration(ABC):
    @abstractmethod
    def create_node(self, id: str, ip: Union[str, IPAddress] = "", mask: str = "", shell: Service = None) -> Node:
        pass

    @abstractmethod
    def create_router(self, id: str, messaging: EnvironmentMessaging) -> Node:
        pass

    @abstractmethod
    def create_interface(self, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0) -> Interface:
        pass

    @abstractmethod
    def add_interface(self, node: Node, interface: Interface, index: int = -1) -> int:
        pass

    @abstractmethod
    def set_interface(self, interface: Interface, ip: Union[str, IPAddress] = "", mask: str = "") -> None:
        pass

    @abstractmethod
    def add_service(self, node: Node, *service: Service) -> None:
        pass

    @abstractmethod
    def set_shell(self, node: Node, service: Service) -> None:
        pass

    @abstractmethod
    def add_route(self, node: Node, *route: Route) -> None:
        pass

    # TODO: This is only temporary - first, it is leaking implementation detail to outside and second, it is
    #       completely stupid, as router should be a designated active service and should provide configuration
    #       interface
    @abstractmethod
    def add_routing_rule(self, node: Node, rule: FirewallRule) -> None:
        pass

    @abstractmethod
    def set_routing_policy(self, node: Node, policy: FirewallPolicy) -> None:
        pass

    @abstractmethod
    def list_routes(self, node: Node) -> List[Route]:
        pass


class ServiceParameter(Flags):
    ENABLE_SESSION = ()
    SESSION_ACCESS_LEVEL = ()


class ServiceConfiguration(ABC):
    @abstractmethod
    def create_active_service(self, id: str, owner: str, name: str, node: Node,
                              service_access_level: AccessLevel = AccessLevel.LIMITED,
                              configuration: Optional[Dict[str, Any]] = None) -> Optional[Service]:
        pass

    @abstractmethod
    def get_service_interface(self, service: ActiveService, control_interface_type: Type[ActiveServiceInterfaceType]) -> ActiveServiceInterfaceType:
        pass

    @abstractmethod
    def create_passive_service(self, id: str, owner: str, version: str = "0.0.0", local: bool = False,
                               service_access_level: AccessLevel = AccessLevel.LIMITED) -> Service:
        pass

    @abstractmethod
    def set_service_parameter(self, service: PassiveService, parameter: ServiceParameter, value: Any) -> None:
        pass

    @abstractmethod
    def create_data(self, id: Optional[str], owner: str, description: str) -> Data:
        pass

    @abstractmethod
    def public_data(self, service: PassiveService) -> List[Data]:
        pass

    @abstractmethod
    def private_data(self, service: PassiveService) -> List[Data]:
        pass

    @abstractmethod
    def public_authorizations(self, service: PassiveService) -> List[Authorization]:
        pass

    @abstractmethod
    def private_authorizations(self, service: PassiveService) -> List[Authorization]:
        pass

    @abstractmethod
    def sessions(self, service: PassiveService) -> List[Session]:
        pass


class NetworkConfiguration(ABC):
    @abstractmethod
    def add_node(self, node: Node) -> None:
        pass

    @abstractmethod
    def add_connection(self, source: Node, target: Node, source_port_index: int = -1, target_port_index: int = -1,
                       net: str = "", connection: Connection = None) -> Connection:
        pass

    @abstractmethod
    def create_session(self, owner: str, waypoints: List[Union[str, Node]], parent: Optional[Session] = None,
                       defer: bool = False, service: Optional[str] = None, reverse: bool = False) -> Optional[Session]:
        pass

    @abstractmethod
    def append_session(self, original_session: Session, appended_session: Session) -> Session:
        pass

    @abstractmethod
    def create_session_from_message(self, message: Message) -> Session:
        pass


class ExploitConfiguration(ABC):
    @abstractmethod
    def create_vulnerable_service(self, id: str, min_version: str = "0.0.0", max_version: str = "0.0.0") -> VulnerableService:
        pass

    @abstractmethod
    def create_exploit_parameter(self, exploit_type: ExploitParameterType, value: str = "", immutable: bool = False) -> ExploitParameter:
        pass

    @abstractmethod
    def create_exploit(self, id: str = "", services: List[VulnerableService] = None, locality:
                       ExploitLocality = ExploitLocality.NONE, category: ExploitCategory = ExploitCategory.NONE,
                       *parameters: ExploitParameter) -> Exploit:
        pass

    @abstractmethod
    def add_exploit(self, *exploits: Exploit) -> None:
        pass

    @abstractmethod
    def clear_exploits(self) -> None:
        pass


class EnvironmentConfiguration(ABC):

    @property
    @abstractmethod
    def node(self) -> NodeConfiguration:
        pass

    @property
    @abstractmethod
    def service(self) -> ServiceConfiguration:
        pass

    @property
    @abstractmethod
    def network(self) -> NetworkConfiguration:
        pass

    @property
    @abstractmethod
    def exploit(self) -> ExploitConfiguration:
        pass
