import uuid
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union, Dict, TypeVar, Type
from netaddr import IPAddress, IPNetwork

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration import ServiceParameter
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.message import Message
from cyst.api.host.service import Service, PassiveService, ActiveService
from cyst.api.logic.action import ActionParameterDomain
from cyst.api.logic.access import Authorization, AccessLevel, AuthenticationTokenType, AuthenticationTokenSecurity,\
    AuthenticationToken, AuthenticationProviderType, AuthenticationProvider, AccessScheme, AuthenticationTarget
from cyst.api.logic.data import Data
from cyst.api.logic.exploit import VulnerableService, ExploitCategory, ExploitLocality, ExploitParameter, ExploitParameterType, Exploit
from cyst.api.network.elements import Connection, Interface, Route
from cyst.api.network.firewall import FirewallRule, FirewallPolicy
from cyst.api.network.session import Session
from cyst.api.network.node import Node


ActiveServiceInterfaceType = TypeVar('ActiveServiceInterfaceType')
ConfigurationObjectType = TypeVar('ConfigurationObjectType')
ObjectType = TypeVar('ObjectType')


class EnvironmentConfiguration(ABC):
    """
    This interface is a collection of configuration interfaces for the environment, that are split according to
    their general functionality.
    """

    @property
    @abstractmethod
    def general(self) -> 'GeneralConfiguration':
        """
        General configuration enables retrieval of objects and their configurations. As such it enables manipulation with
        all objects that are present in the simulation run.

        :rtype: GeneralConfiguration
        """

    @property
    @abstractmethod
    def node(self) -> 'NodeConfiguration':
        """
        Node configuration enables creation and manipulation with nodes and routers.

        :rtype: NodeConfiguration
        """

    @property
    @abstractmethod
    def service(self) -> 'ServiceConfiguration':
        """
        Service configuration enables management of passive and active services.

        :rtype: ServiceConfiguration
        """

    @property
    @abstractmethod
    def network(self) -> 'NetworkConfiguration':
        """
        Network configuration enables placing nodes inside the topology and manipulation with connection and sessions.
        Currently it is mostly additive, but it will include all manipulation options in the future.

        :rtype: NetworkConfiguration
        """

    @property
    @abstractmethod
    def exploit(self) -> 'ExploitConfiguration':
        """
        This interface provides means to manipulate with exploits.

        :rtype: ExploitConfiguration
        """

    @property
    @abstractmethod
    def action(self) -> 'ActionConfiguration':
        """
        Action configuration enables creation of action parameter domains. While the actions are fully declarative in their
        description and their semantics stem from the interpretation given by behavioral models, action parameters enable
        fine-tuning of actions, that is accessible to automatic tools in a uniform manner.

        :rtype: ActionConfiguration
        """

    @property
    @abstractmethod
    def access(self) -> 'AccessConfiguration':
        """
        Access configuration enables manipulation of authentication and authorization primitives, creation of access schemes
        and evaluation of authentication tokens.

        :rtype: AccessConfiguration
        """


class GeneralConfiguration(ABC):
    """
    General configuration enables retrieval of objects and their configurations. As such it enables manipulation with
    all objects that are present in the simulation run.
    """
    @abstractmethod
    def get_configuration(self) -> List[ConfigItem]:
        """
        Get the entire configuration of the environment in form of a list containing top level configuration objects,
        i.e., nodes, connections, and exploits. There are no inter-object references, they are all resolved, so there
        is a potential duplication.

        :return: A complete environment configuration.
        """

    @abstractmethod
    def save_configuration(self, indent: Optional[int]) -> str:
        """
        Serializes a configuration into a string representation, that can be saved and later loaded and passed to the
        configure() method.

        :param indent: The indentation level for pretty-printing. If not provided, the configuration is serialized onto
                       one line. If indent is set to 0, only line breaks are inserted. If indent is set to 1 or more
                       the text is indented accordingly.
        :type indent: Optional[int]

        :return: A string representation of the environment's configuration.
        """

    @abstractmethod
    def load_configuration(self, config: str) -> List[ConfigItem]:
        """
        Deserializes a string configuration into corresponding configuration items. These are currently not guaranteed
        to work across versions.

        :param config: The serialized configuration.
        :type config: str

        :return: A list of configuration items that can be fed to the configure() function.
        """

    @abstractmethod
    def get_configuration_by_id(self, id: str, configuration_type: Type[ConfigurationObjectType]) -> ConfigurationObjectType:
        """
        Get a ...Config object by ID.

        :param id: The ID of the configuration object.
        :type id: str

        :param configuration_type: A type of the configuration item to get. While not technically necessary, given the
            state of Python's type system, it is there to satisfy static typing inspection.
        :type configuration_type: Type[TypeVar('ConfigurationObjectType')]

        :return: A configuration object with given ID.
        """

    @abstractmethod
    def get_object_by_id(self, id: str, object_type: Type[ObjectType]) -> ObjectType:
        """
        Get any object instantiated within a simulation.

        :param id: The ID of the object.
        :type id: str

        :param object_type: A type of object to get. While not technically necessary, given the state of Python's type
            system, it is there to satisfy static typing inspection.
        :type object_type: Type[TypeVar('ObjectType')]

        :return: An object with give ID.
        """


class NodeConfiguration(ABC):
    """
    Node configuration enables creation and manipulation with nodes and routers.
    """
    @abstractmethod
    def create_node(self, id: str, ip: Union[str, IPAddress] = "", mask: str = "", shell: Service = None) -> Node:
        """
        Create a node within a simulation. The node itself is empty and must be filled with services before it can
        interact with the environment. The same goes for its network connection, unless provided in the constructor.

        :param id: A unique identification of the node within the simulation. Setting a duplicate ID would result in
            an exception.
        :type id: str

        :param ip: An IP address this node should use. Setting this parameter automatically creates the appropriate
            network interface. The address can be passed as a string or as an IPAddress, into which it is internally
            converted from the string.
        :type ip: Union[str, IPAddress]

        :param mask: A network mask to use. This will be used for setting the gateway and routing policy on the node.
            If the mask is not selected, it gets negotiated during a connection with the router (TODO: check).
        :type mask: str

        :param shell: A service that will be acting as a system shell.
        :type shell: Service

        :return: An instance of a node in the simulation.
        """

    @abstractmethod
    def create_router(self, id: str, messaging: EnvironmentMessaging) -> Node:
        """
        Create a router within simulation. The router is a special type of node, which enables message forwarding and
        network partitioning.

        :param id: A unique identification of the node within simulation.  Setting a duplicate ID would result in
            an exception.
        :type id: str

        :param messaging: A reference to EnvironmentMessaging
        :type messaging: EnvironmentMessaging

        :return: An instance of a router in the simulation.
        """

    @abstractmethod
    def create_port(self, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0, id: str = "") -> Interface:
        """
        Create a network port, which can then be used to connect routers to routers.

        :param ip: An IP address of the port. If not set, it will be a port without IP and the routing will have to be
            explicitly specified.
        :type ip: Union[str, IPAddress]

        :param mask: A network mask of the port. It is used to signal the network range serviced by the router.
        :type mask: str

        :param index: An index the port should have. If a value -1 is selected, the interface is assigned a lowest
            possible index.
        :type index: int

        :param id: A unique identification of the interface within the simulation. If no value is provided, the system
                   will generate a unique one.
        :type id: str

        :return: An instance of a network port.
        """
        pass

    @abstractmethod
    def create_interface(self, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0, id: str = "") -> Interface:
        """
        Create a network interface, which can then be used to connect nodes to routers or routers to routers.

        :param ip: An IP address of the interface. If not set, it will act as a DHCP interface for nodes and an IP-less
            port for routers.
        :type ip: Union[str, IPAddress]

        :param mask: A network mask of the interface. In case of a node interface it will be used for setting the
            gateway and routing policy on the node. If the mask is not selected, it gets negotiated during a connection
            with the router. In case of router port, the mask is used to determine the pool for DHCP addresses.
        :type mask: str

        :param index: An index the port should have, once assigned to a node. If a value -1 is selected, the interface
            is assigned a lowest possible index.
        :type index: int

        :param id: A unique identification of the interface within the simulation. If no value is provided, the system
                   will generate a unique one.
        :type id: str

        :return: An instance of a network interface.
        """

    @abstractmethod
    def create_route(self, net: IPNetwork, port: int, metric: int, id: str = "") -> Route:
        """
        Create a route, which determines through which port messages directed to particular network get sent.

        :param net: A destination network, which is being routed through the specified port.
        :type net: IPNetwork

        :param port: A port index. If a nonexistent port is selected, it will raise an exception, when a message will
            be routed through it.
        :type port: int

        :param metric: A metric for the route. Routes with lower metric get selected when there is an overlap in
            their networks. In case of metric equivalence, more specific routes are selected.
        :type metric: int

        :param id: A unique identification of the route within the simulation. If no value is provided, the system
                   will generate a unique one.
        :type id: str

        :return: A route to be used in router.
        """

    @abstractmethod
    def add_interface(self, node: Node, interface: Interface, index: int = -1) -> int:
        """
        Assigns a network interface instance to a node.

        :param node: A node instance to assign the interface to.
        :type node: Node

        :param interface: An interface instance to be assigned.
        :type interface: Interface

        :param index: An index to give the interface. If left at -1, a lowest possible index is given to the interface.
            If an already occupied index is given, an exception is thrown.

        :return: An index, where the interface was assigned.
        """

    @abstractmethod
    def set_interface(self, interface: Interface, ip: Union[str, IPAddress] = "", mask: str = "") -> None:
        """
        Sets parameters of an interface instance.

        :param interface: The instance of the interface.
        :type interface: Interface

        :param ip: A new IP address to use. Setting this to an empty string will effectively erase the IP address from
            the interface. In that case, it can only work in routers with explicit routing.
        :type ip: Union[str, IPAddress]

        :param mask: A new network mask.
        :type mask: str

        :return: None
        """

    @abstractmethod
    def add_service(self, node: Node, *service: Service) -> None:
        """
        Add a service to the node. The engine expects that there aren't two services of the same name on one node. In
        such case, the effects are undefined.

        :param node: An instance of a node to assign the service to.
        :type node: Node

        :param service: One or more service instances to assign.
        :type service: Service

        :return: None
        """

    @abstractmethod
    def remove_service(self, node: Node, *service: Service) -> None:
        """
        Remove a service from the node.

        :param node: An instance of a node to remove the service from.
        :type node: Node

        :param sertice: One or more service instances to remove.
        :type service: Service

        :return: None
        """

    @abstractmethod
    def set_shell(self, node: Node, service: Service) -> None:
        """
        Set given service as a shell. Unlike the method add_service, set_shell does not produce undefined results, when
        a service already present at the node is set as a shell.

        :param node: An instance of a node to set shell at.
        :type node: Node

        :param service: An instance of a service to set.
        :type service: Service

        :return: None
        """

    @abstractmethod
    def add_traffic_processor(self, node: Node, processor: ActiveService) -> None:
        """
        Add a service to a traffic processor queue. Traffic processors process messages incoming into a node before any
        evaluation takes place. There can be multiple traffic processors on one node and their order depends on the
        order of add_traffic_processor calls. The first one added, processes the traffic first, and so on...

        Any active service can be set as a traffic processor. Traffic processors are free to change the contents of
        messages and unless they return False from their process_message() function that message is passed to next
        processors or to the node.

        :param node: An instance of the node where traffic processor should be added.
        :type node: Node

        :param processor: An instance of an active service which will act as a traffic processor.
        :type processor: ActiveService

        :return: None
        """

    @abstractmethod
    def add_route(self, node: Node, *route: Route) -> None:
        """
        Add a network route to a router.

        :param node: An instance of the router. Although the type is set as a Node here, this function can only be
            called on routers. Trying to assign a route to an ordinary node would do nothing.
        :type node: Node

        :param route: On or more network routes to add.
        :type route: Route

        :return: None
        """

    @abstractmethod
    def add_routing_rule(self, node: Node, rule: FirewallRule) -> None:
        """
        Adds a rule for source-destination routing. This effectively bypasses the routing rules and enables custom
        port forwarding.

        TODO
            This is only temporary - first, it is leaking implementation detail to outside and second, it is
            completely stupid, as router should be a designated active service and should provide configuration
            interface.

        :param node: An instance of a router. Although the type is set as a Node here, this function can only be
            called on routers. Trying to add a routing rule to an ordinary node would do nothing.
        :type node: Node

        :param rule: A firewall rule, which coincidentally has all the necessary ingredients for implementation of
            source-destination routing. See the TODO on why this is a stupid idea.
        :type rule: FirewallRule

        :return: None
        """

    @abstractmethod
    def set_routing_policy(self, node: Node, policy: FirewallPolicy) -> None:
        """
        Sets a default routing policy for source-destination routing.

        The same comment regarding the stupidity of this interface applies as an function add_routing_rule().

        :param node: An instance of a router. Although the type is set as a Node here, this function can only be
            called on routers. Trying to assign a routing policy to an ordinary node would do nothing.

        :param policy: A firewall policy, which coincidentally has all the necessary ingredients for implementation of
            source-destination routing policy. See the add_routing_rule() on why this is a stupid idea.
        :type policy: FirewallPolicy

        :return: None
        """

    @abstractmethod
    def list_routes(self, node: Node) -> List[Route]:
        """
        List all the routes currently set at a router.

        TODO
            This will be changed in the future, after router is implemented as an active service with its own interface.

        :param node: The router to get routes from. Although the type is set as a Node here, this function can only be
            called on routers. Trying to list routes from an ordinary node would do nothing.
        :type node: Node

        :return: A list of routes.
        """


class ServiceConfiguration(ABC):
    """
    Service configuration enables management of passive and active services.
    """
    @abstractmethod
    def create_active_service(self, type: str, owner: str, name: str, node: Node,
                              service_access_level: AccessLevel = AccessLevel.LIMITED,
                              configuration: Optional[Dict[str, Any]] = None, id: str = "") -> Optional[Service]:
        """
        Creates an active service. These include anything from traffic processors to agents.

        :param type: A type of the service, which is a unique identification among services.
        :type type: str

        :param id: An ID that will be given to the service and which must be unique within the simulation environment.
        :type id: str

        :param owner: An identity that will own the service at the node. While it should be an identity that is present
            at the node, this is currently not controlled in any way, because the whole identity business is not yet
            sorted out.
        :type owner: str

        :param name: The name of the service as it was registered into the system. (see cyst.api.host.service.ActiveServiceDescription)
        :type name:  str

        :param node: An instance of a node where the service will reside in the end. There is a technical limitation
            that lies behind this requirement. If it weren't there, everything would be done in the add_service() call.
        :type node: Node

        :param service_access_level: An access level for the service. This mostly concerns the resources of the Node it
            can access.
        :type service_access_level: AccessLevel

        :param configuration: A dictionary of configuration parameters. There are no limitations to the param/value
            pairs, as they are directly passed to function creation function. (see cyst.api.host.service.ActiveServiceDescription)
        :type configuration: Optional[Dict[str, Any]]

        :param id: An ID that will be given to the service and which must be unique within the simulation environment.
                   If no ID is provided a unique one is generated.
        :type id: str

        :return: An instance of an active service, or null if failed to create one.
        """

    @abstractmethod
    def get_service_interface(self, service: ActiveService, control_interface_type: Type[ActiveServiceInterfaceType]) -> ActiveServiceInterfaceType:
        """
        Active services can provide an interface, which enables a finer control over their function than a rather
        limited cyst.api.host.service.ActiveService interface.

        Due to python's handling of types and interfaces, you can always just call the functions of the service
        directly, without going through the hassle of interface acquisition, but such approach would not pass through
        a static verification.

        Example:

        .. code-block:: python

            from cyst.api.environment.environment import Environment
            from cyst.services.scripted_attacker.main import ScriptedAttackerControl

            env = Environment.create()
            node = env.configuration.node.create_node("node1")
            service = env.configuration.service.create_active_service("attacker1", "attacker", "scripted_attacker", node)
            ctrl = env.configuration.service.get_service_interface(service.active_service, ScriptedAttackerControl)

            ctrl.execute_action(...)

        :param service: An instance of an active service. Please consult the example and the Service interface to
            prevent unwanted surprises (.active_service).
        :type service: ActiveService

        :param control_interface_type: A type of the interface that should be obtained from the service. Note that a
            service can provide multiple interfaces.
        :type control_interface_type: Type[TypeVar('ActiveServiceInterfaceType')]

        :return: An interface of a service.
        """

    @abstractmethod
    def create_passive_service(self, type: str, owner: str, version: str = "0.0.0", local: bool = False,
                               service_access_level: AccessLevel = AccessLevel.LIMITED, id: str = "") -> Service:
        """
        Create a passive service.

        :param type: A type of the service, such as lighttpd or bash. The type is relevant for mapping exploits.
        :type type: str

        :param owner: An identity that will own the service at the node. While it should be an identity that is present
            at the node, this is currently not controlled in any way, because the whole identity business is not yet
            sorted out.
        :type owner: str

        :param version: The version of the service. The format of the version should be compatible with semantic
            versioning scheme. TODO: Extend the signature to Union[str, VersionInfo]
        :type version: str

        :param local: An indication, whether the service is accessible from outside the node.
        :type local: bool

        :param service_access_level: An access level of the service. This mostly concerns the resources than can be
            accessed in case of service compromise.
        :type service_access_level: AccessLevel

        :param id: A unique ID within the simulation. An ID is generated if not provided.
        :type id: str

        :return: An instance of passive service.
        """

    @abstractmethod
    def update_service_version(self, service: PassiveService, version: str = "0.0.0") -> None:
        """
        Changes the service version to a new value. This function is primarily meant as a way to simulate updates
        or patching of already running services.

        :param service: An instance of the passive service.
        :type service: PassiveService

        :param version: A new value of the version. The format of the version should be compatible with semantic
            versioning scheme. TODO: Extend the signature to Union[str, VersionInfo]
        :type version: str

        :return: None
        """

    @abstractmethod
    def set_service_parameter(self, service: PassiveService, parameter: ServiceParameter, value: Any) -> None:
        """
        Sets a parameter of an existing passive service. The parameters are chosen from a parametrization domain
        defined by the ServiceParameter flags.

        :param service: An instance of the passive service.
        :type service: PassiveService

        :param parameter: A type of the parameter to set.
        :type parameter: ServiceParameter

        :param value: A value of the parameter. For allowed values, consult cyst.api.environment.configuration.ServiceParameter.
        :type value: Any

        :return: None
        """

    @abstractmethod
    def create_data(self, id: Optional[str], owner: str, description: str) -> Data:
        """
        Creates a data. Currently this is a very rudimentary approach and future updates are expected to provide more
        sophisticated mechanisms for data description and manipulation.

        :param id: An optional identification of the data.
        :type id: Optional[str]

        :param owner: An identity of the owner of the data. This should be an identity existing within the simulation
            (not necessarily on the node and service where the data will reside), as the access to the data should be
            checked against the name in the authentication token, which has to be the same as the owner. [That "should"
            here means that it is dependent on the implementation of behavioral models.]
        :type owner: str

        :param description: A textual description of the data, which currently enables differentiation between data
            instances.
        :type description: str

        :return: An instance of data.
        """

    @abstractmethod
    def public_data(self, service: PassiveService) -> List[Data]:
        """
        Gets access to the data that should be available on the service without the need for authentication. This can
        be used both to get and set the data.

        :param service: An instance of the passive service.
        :type service: PassiveService

        :return: A list of public data instances on the service.
        """

    @abstractmethod
    def private_data(self, service: PassiveService) -> List[Data]:
        """
        Gets access to the data that should be available on the service only after authentication. This can
        be used both to get and set the data.

        :param service: An instance of the passive service.
        :type service: PassiveService

        :return: A list of private data instances on the service.
        """

    @abstractmethod
    def public_authorizations(self, service: PassiveService) -> List[Authorization]:
        """
        Gets access to public authorizations present at the service.

        Warning:
            This function is deprecated and will be removed soon, as it does not conform to the current
            authentication/authorization framework.

        :param service: An instance of the passive service.
        :type service: PassiveService

        :return: A list of publicly available authorization instances.
        """

    @abstractmethod
    def private_authorizations(self, service: PassiveService) -> List[Authorization]:
        """
        Gets access to private authorizations present at the service.

        Warning:
            This function is deprecated and will be removed soon, as it does not conform to the current
            authentication/authorization framework.

        :param service: An instance of the passive service.
        :type service: PassiveService

        :return: A list of privately available authorization instances.
        """

    @abstractmethod
    def sessions(self, service: PassiveService) -> List[Session]:
        """
        Gets access to sessions that are connected to the service. These sessions can either be the ones created as
        a part of the initialization process, or those that were created following the activities in the simulation.

        :param service: An instance of the passive service.
        :type service: PassiveService

        :return: A list of sessions connected to the service.
        """

    @abstractmethod
    def provides_auth(self, service: Service, auth_provider: AuthenticationProvider) -> None:
        """
        Adds an authentication provider to a service.

        TODO
            This function, if it is really intended to stay, must be renamed to something better, such as add_auth_provider.
            Also the parameter type should be checked, because the implementation conflates Service and PassiveService.

        :param service: An instance of the passive service.
        :type service: Service (but should be PassiveService)

        :param auth_provider: An authentication provider to add.
        :type auth_provider: AuthenticationProvider

        :return: None
        """

    @abstractmethod
    def set_scheme(self, service: PassiveService, scheme: AccessScheme) -> None:
        """
        Sets and authentication scheme at the service. More on authentication schemes at the user's documentation or in
        the documentation of cyst.api.logic.access.

        :param service: An instance of the passive service.
        :type service: PassiveService

        :param scheme: An instance of the access scheme.
        :type scheme: AccessScheme

        :return: None
        """


class NetworkConfiguration(ABC):
    """
    Network configuration enables placing nodes inside the topology and manipulation with connection and sessions.
    Currently it is mostly additive, but it will include all manipulation options in the future.
    """
    @abstractmethod
    def add_node(self, node: Node) -> None:
        """
        Adds a node into the topology. After a node is created, it must be added to the simulation topology. Otherwise
        it will not be included in messaging. Note that this is done implicitly when using declarative configuration,
        so this mostly concerns scenarios, such as honeypot deployment.

        :param node: An instance of the node.
        :type node: Node

        :return: None
        """

    @abstractmethod
    def add_connection(self, source: Node, target: Node, source_port_index: int = -1, target_port_index: int = -1,
                       net: str = "", connection: Optional[Connection] = None) -> Connection:
        """
        Adds a connection between two nodes, provided each one has a network port available. If one of the nodes is
        router, it may trigger DHCP address assignment, depending on the settings of node interfaces.

        :param source: An instance of the source node. Connections are currently bi-directional, so it does not
            matter which one is the source and which one is the destination.
        :type source: Node

        :param target: An instance of the destination node.
        :type target: Node

        :param source_port_index: An index of the interface at the source node. If the index does not point to an
            existing interface, an exception will be thrown.
        :type source_port_index: int

        :param target_port_index: An index of the interface at the destination node. If the index does not point to an
            existing interface, an exception will be thrown.
        :type target_port_index: int

        :param net: A network mask specification, used by a router (if one is present) to determine a correct address
            range. This parameter is not necessary, if all addresses are fully specified in the interfaces.
        :type net: str

        :param connection: An instance of a connection. This parameter enables passing a specific connection instance,
            which has, e.g., specific connection properties. If this parameter is omitted, then a new connection is
            automatically created.
        :type connection: Connection

        :return: An instance of a connection that was established between selected nodes.
        """

    @abstractmethod
    def get_connections(self, node: Node, port_index: Optional[int] = None) -> List[Connection]:
        """
        Gets connections that are connected to the node at the port index, if specified.

        :param node: An instance of the node.
        :type node: Node

        :param port_index: An index of the port.
        :type port_index: Optional[int]

        :return: A list of connections that are connected to the node.
        """

    @abstractmethod
    def create_session(self, owner: str, waypoints: List[Union[str, Node]], src_service: Optional[str] = None,
                       dst_service: Optional[str] = None, parent: Optional[Session] = None, defer: bool = False,
                       reverse: bool = False) -> Optional[Session]:
        """
        Creates a fixed session in the simulated infrastructure. This session ignores the routing limitations imposed
        by router configuration. However, the creation mechanism checks if there exists a connection between each of
        session waypoints and it selects the appropriate interfaces to realize the connection through.

        :param owner: The owner of the session. This parameter is used to prevent sharing of sessions, but it will
            likely be deprecated in future versions, because it does not work well when appending sessions through
            exploiting.
        :type owner: str

        :param waypoints: A list of node instances or their IDs, which constitute the path of the session. As per
            the description, there has to be a connection between all subsequent tuples of waypoints.
        :type waypoints: List[Union[str, Node]]

        :param src_service: An ID of the service that is the anchor at the origin of the session. This service can
                            tear down the session at will.
        :type src_service: Optional[str]

        :param dst_service: An ID of the service that is the anchor at the destination of the session. This service can
                            tear down the session at will.
        :type dst_service: Optional[str]

        :param parent: A parent session that can be optionally used as a first part/head of the session.
        :type parent: Optional[Session]

        :param defer: I this parameter is set to False, the system attempts to create the session immediately. If set to
            False, the creation is deferred to the environment init phase, when all the waypoints should already be
            instantiated.
        :type defer: bool

        :param reverse: Construct the session in the reverse order, i.e., as if it was constructed as a reverse shell.
        :type reverse: bool

        :return: An instance of a created session (unless deferred, than it always return null)
        """

    @abstractmethod
    def append_session(self, original_session: Session, appended_session: Session) -> Session:
        """
        Creates a new session by appending a two sessions together.

        :param original_session: The session that will serve as a beginning of the session. At its endpoint the
            second session will be appended.
        :type original_session: Session

        :param appended_session: The session that will serve as the end of the session. It will be connected to the
            original session with its startpoint.
        :type appended_session: Session

        :return: A new session that is a combination of both the original ones.
        """

    @abstractmethod
    def create_session_from_message(self, message: Message) -> Session:
        """
        Establishes a new session from the path the message travelled. This function is mostly used by behavioral models
        to create new sessions in response to messages coming from attackers.

        :param message: An instance of the message.
        :type message: Message

        :return: A new session.
        """


class ExploitConfiguration(ABC):
    """
    This interface provides means to manipulate with exploits.
    """
    @abstractmethod
    def create_vulnerable_service(self, id: str, min_version: str = "0.0.0", max_version: str = "0.0.0") -> VulnerableService:
        """
        Create a definition of a vulnerable service, that is used for exploit specification

        :param name: A name of the service. It is an equivalent of PassiveService/PassiveServiceConfig name.
        :type name: str

        :param min_version: A minimum version of the service that is vulnerable. Even though the type supports any string,
            using anything else than string representation of a semantic version will lead to problems.
        :type min_version: str

        :param max_version: A maximum version of the service that is vulnerable. Even though the type supports any string,
            using anything else than string representation of a semantic version will lead to problems.
        :type max_version: str

        :return: A vulnerable service description.
        """

    @abstractmethod
    def create_exploit_parameter(self, exploit_type: ExploitParameterType, value: str = "", immutable: bool = False) -> ExploitParameter:
        """
        Creates an exploit parameter.

        Exploit parameter either represents a specification of an exploit, which can't be modified by a user, but is
        taken into account by exploit evaluation mechanisms (e.g., if the impact is one user or all users), or provides a
        mean for a user to supply additional information necessary for full execution of the exploit (e.g., identity of
        a user to impersonate).

        :param type: A type of the exploit parameter.
        :type type: ExploitParameterType

        :param value: A value of the parameter.
        :type value: Optional[str]

        :param immutable: A flag indicating, whether a user can change the value of the parameter.
        :type immutable: bool

        :return: An instance of exploit parameter.
        """

    @abstractmethod
    def create_exploit(self, id: str = "", services: List[VulnerableService] = None, locality:
                       ExploitLocality = ExploitLocality.NONE, category: ExploitCategory = ExploitCategory.NONE,
                       *parameters: ExploitParameter) -> Exploit:
        """
        Creates a working exploit.
        
        If a definition of exploit exists, then a services it refers to are vulnerable, as long as their version match.
        Patching the service and bumping a version over the max vulnerable version is the only countermeasure.

        :param id: A unique identification of the exploit.
        :type id: str 
        
        :param services: A list of services that are vulnerable to this exploit.
        :type services: List[VulnerableService]
    
        :param locality: Determines if the exploit can be used locally or remotely.
        :type locality: ExploitLocality
    
        :param category: Determines the category of the exploit.
        :type category: ExploitCategory
    
        :param parameters: An optional list of exploit parameters.
        :type parameters: Optional[List[ExploitParameter]]
        
        :return: An instance of the exploit.
        """

    @abstractmethod
    def add_exploit(self, *exploits: Exploit) -> None:
        """
        Adds an exploit to the exploit store, where it can be accessed by the services. Unless an exploit is added to
        the store, it cannot be used, even though it was created.

        :param exploits: One or more exploit instances to be added.
        :type exploits: Exploit

        :return: None
        """

    @abstractmethod
    def clear_exploits(self) -> None:
        """
        Removes all exploits from exploit store.

        :return: None
        """


class ActionConfiguration(ABC):
    """
    Action configuration enables creation of action parameter domains. While the actions are fully declarative in their
    description and their semantics stem from the interpretation given by behavioral models, action parameters enable
    fine-tuning of actions, that is accessible to automatic tools in a uniform manner.
    """
    @abstractmethod
    def create_action_parameter_domain_any(self) -> ActionParameterDomain:
        """
        Create an action parameter domain that can accept any parameter. This domain should be avoided at all costs,
        because it does not provide anything for automated tools to work with.

        :return: An unbounded parameter domain.
        """

    @abstractmethod
    def create_action_parameter_domain_range(self, default: int, min: int, max: int, step: int = 1) -> ActionParameterDomain:
        """
        Creates a parameter domain that is represented by a range of numbers. Ideal for expressing things like port
        ranges.

        :param default: A default value of the domain.
        :type default: int

        :param min: A minimal range value.
        :type min: int

        :param max: A maximal range value.
        :type max: int

        :param step: Enables to include only every step-th number between min and max.
        :type step: int

        :return: A parameter domain consisting of range of numbers.
        """

    @abstractmethod
    def create_action_parameter_domain_options(self, default: Any, options: List[Any]) -> ActionParameterDomain:
        """
        Creates a parameter domain that is represented by a set of possible values. The values are not limited in any
        way, but this enables automated tools to select from them.

        :param default: A default value of the domain.
        :type default: Any

        :param options: A list of values, which constitute the domain.
        :type options: List[Any]

        :return: A parameter domain consisting of set of values.
        """


class AccessConfiguration(ABC):
    """
    Access configuration enables manipulation of authentication and authorization primitives, creation of access schemes
    and evaluation of authentication tokens.
    """
    @abstractmethod
    def create_authentication_provider(self, provider_type: AuthenticationProviderType,
                                       token_type: AuthenticationTokenType, security: AuthenticationTokenSecurity,
                                       ip: Optional[IPAddress], timeout: int, id: str = "") -> AuthenticationProvider:
        """
        Authentication provider represents an authentication mechanism that can be employed in services via the access
        scheme mechanism.

        :param provider_type: The type of authentication provider.
        :type provider_type: AuthenticationProviderType

        :param token_type: The type of tokens that are employed by this authentication provider.
        :type token_type: AuthenticationTokenType

        :param token_security: Security mechanism applied to stored tokens.
        :type token_security: AuthenticationTokenSecurity

        :param ip: An optional IP address, which is intended for remote or federated providers. It represents an IP
            address where this provider can be accessed.
        :type ip: Optional[IPAddress]

        :param timeout: A number of simulated time units that can elapse from the initiation of authentication exchange
            before the attempt is discarded as unsuccessful.
        :type timeout: int

        :param id: A unique identification of the provider within the simulation. If no value is provided, the system
                   will generate a unique one.
        :type id: str

        :return: An authentication provider instance.
        """

    @abstractmethod
    def create_authentication_token(self, type: AuthenticationTokenType, security: AuthenticationTokenSecurity,
                                    identity: str, is_local: bool) -> AuthenticationToken:
        """
        Creates an authentication token for a given identity. This token is given a unique identifier, which
        distinguishes it from other tokens.

        Warning:
            The documentation is missing the description of the is_local parameter and it implications

        :param type: A type of the authentication token.
        :type type: AuthenticationTokenType

        :param security: A level of security for the authentication token.
        :type security: AuthenticationTokenSecurity

        :param identity: A identity this token is bound to. In theory, no identity needs to be provided (such as
            access code to doors). However, not using it here may have unintended consequences.

        :param is_local: No idea...
        :type is_local: bool

        :return: An instance of authentication token.
        """

    @abstractmethod
    def register_authentication_token(self, provider: AuthenticationProvider, token: AuthenticationToken) -> bool:
        """
        Registers an authentication token with the authentication provider. After that, anyone possessing the token
        can authenticate against the provider.

        :param provider: An instance of the authentication provider.
        :type provider: AuthenticationProvider

        :param token: An instance of the authentication token.
        :type token: AuthenticationToken

        :return: Indication, whether registration was successful.
        """

    @abstractmethod
    def unregister_authentication_token(self, token_identity: str, provider: AuthenticationProvider) -> None:
        """
        Unregisters authentication token from given provider based on given token identity.

        :param token_identity: An identity for token to be unregistered from provider.
        :type token_identity: str

        :param provider: An authentication provider to unregister token from.
        :type provider: AuthenticationProvider

        :return: None
        """

    @abstractmethod
    def create_and_register_authentication_token(self, provider: AuthenticationProvider, identity: str) -> Optional[AuthenticationToken]:
        """
        A convenience function that combines the effects of create_authentication_token() and
        register_authentication_token().

        :param provider: An instance of the authentication provider.
        :type provider: AuthenticationProvider

        :param identity: A identity the created token is bound to. In theory, no identity needs to be provided (such as
            access code to doors). However, not using it here may have unintended consequences.
        :type identity: str

        :return: An instance of authentication token that is already registered.
        """

    @abstractmethod
    def create_authorization(self, identity: str, access_level: AccessLevel, id: str, nodes: Optional[List[str]] = None,
                             services: Optional[List[str]] = None) -> Authorization:
        """
        Creates and authorization for a given identity. The authorization gives the identity access to selected nodes
        and services with a given access level.

        :param identity: An identity for whom the authorization is created.
        :type identity: str

        :param access_level: An access level this authorization provides.
        :type access_level: AccessLevel

        :param id: A unique identifier of this authorization. TODO: I have no idea, what is the purpose.
        :type id: str

        :param nodes: A list of node ids this authorization works on. This is intended for federated identities, which
            can are shared among different nodes and services. For local authentication providers, this parameters
            is of no use.
        :type nodes: Optional[List[str]]

        :param services: A list of service ids this authorization works on. This is intended for federated identities,
            which can are shared among different nodes and services. For local authentication providers, this parameters
            is of no use.
        :type services: Optional[List[str]]

        :return: An authorization token.
        """

    @abstractmethod
    def create_access_scheme(self, id: str = "") -> AccessScheme:
        """
        Creates an empty access scheme. The access scheme is a combination of authentication providers, which use a
        supplied authorizations. The access scheme provides means to describe multiple authentication schemes
        within one service or multi-factor authentication.

        :param id: A unique identification of the scheme within the simulation. If no value is provided, the system
                   will generate a unique one.
        :type id: str

        :return: An empty access scheme.
        """

    @abstractmethod
    def add_provider_to_scheme(self, provider : AuthenticationProvider, scheme: AccessScheme) -> None:
        """
        Adds an authentication provider to the access scheme.

        :param provider: An authentication provider.
        :type provider: AuthenticationProvider

        :param scheme: An access scheme to add provider to.
        :type scheme: AccessScheme

        :return: None
        """

    @abstractmethod
    def add_authorization_to_scheme(self, auth: Authorization, scheme: AccessScheme) -> None:
        """
        Adds an authorization to the access scheme.

        :param auth: An instance of authorization.
        :type auth: Authorization

        :param scheme: An access scheme to add authorization to.
        :type scheme: AccessScheme

        :return: None
        """

    @abstractmethod
    def remove_authorization_from_scheme(self, auth: Authorization, scheme: AccessScheme) -> None:
        """
        Removes given authorization from given scheme by setting its access level to AccessLevel.NONE

        :param auth: An authorization to be removed from scheme.
        :type auth: Authorization

        :param scheme: A scheme.
        :type scheme: AccessScheme

        :return: None
        """

    @abstractmethod
    def evaluate_token_for_service(self, service: Service, token: AuthenticationToken, node: Node,
                                   fallback_ip: Optional[IPAddress])\
            -> Optional[Union[Authorization, AuthenticationTarget]]:
        """
        Evaluates if a token authenticates against a service. For single-factor authentications, this function returns
        either a working authorization token or none, depending on success. For multi-factor authentications, if it is
        the last factor, then it behaves as a single-factor authentication. If it is not, then it will either return a
        next authentication target in given scheme or none, depending on success.

        TODO
            Add the description of fallback_ip.

        :param service: An instance of the service the evaluation is against.
        :type service: Service

        :param token: An instance of the authentication token.
        :type token: AuthenticationToken

        :param node: An instance of the node where the service resides on.
        :type node: Node

        :param fallback_ip: No idea
        :type fallback_ip: Optional[IPAddress]

        :return: Either a working authorization, a next target, or just none if the authentication was not successful.
        """

    @abstractmethod
    def disable_authentication_token(self, provider: AuthenticationProvider, token: AuthenticationToken, time: int) -> None:
        """
        Disables given token until given simulation time.

        :param provider: An authentication provider that contains token to be disabled.
        :type provider: AuthenticationProvider

        :param token: An authentication token to be disabled.
        :type token: AuthenticationToken

        :param time: Simulation time
        :type time: int

        :return: None
        """

    @abstractmethod
    def enable_authentication_token(self, provider: AuthenticationProvider, token: AuthenticationToken) -> None:
        """
        Enables given token.

        :param provider: An authentication provider that contains token to be enabled.
        :type provider: AuthenticationProvider

        :param token: An authentication token to be enabled.
        :type token: AuthenticationToken

        :return: None
        """

    @abstractmethod
    def create_service_access(self, service: Service, identity: str, access_level: AccessLevel,
                              tokens: List[AuthenticationToken] = None) -> Optional[List[AuthenticationToken]]:
        """
        Create a means to access the given passive service by registering authentication tokens
        under the given identity.

        TODO: Currently works only for local providers.

        :param service: A passive service to grant access to.
        :type service: PassiveService

        :param identity: An identity of the user which will gain the access.
                         It must not be already present in one of the access schemes.
        :type identity: str

        :param access_level: The level of access which will be created.
        :type access_level: AccessLevel

        :param tokens: Tokens to be optionally used instead of creating new ones.
        :type tokens: List[AuthenticationToken]

        :return: List of authentication tokens if successful, None otherwise.
        """

    @abstractmethod
    def modify_existing_access(self, service: Service, identity: str, access_level: AccessLevel) -> bool:
        """
        Modify the access level of the given passive service. No new tokens are created.

        TODO: Currently works only for local providers.

        :param service: A passive service to grant access to.
        :type service: PassiveService

        :param identity: An identity of the user which access will be modified.
                         It must be already present at one of the access scheme.
        :type identity: str

        :param access_level: The level of access which will be modified.
        :type access_level: AccessLevel

        :return: True if successful, False otherwise.
        """
