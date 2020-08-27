import importlib

from heapq import heappush, heappop
from itertools import product
from typing import Tuple, List, Union, Optional, Any, Dict

from netaddr import IPAddress

from cyst.api.environment.environment import Environment
from cyst.api.environment.control import EnvironmentState, EnvironmentControl
from cyst.api.environment.configuration import EnvironmentConfiguration, NodeConfiguration, ServiceConfiguration, NetworkConfiguration, ServiceParameter, ExploitConfiguration
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.message import Message, MessageType, Request, StatusValue, StatusOrigin, Status, Response
from cyst.api.environment.interpreter import ActionInterpreterDescription
from cyst.api.environment.stores import ServiceStore, ActionStore, ExploitStore
from cyst.api.network.elements import Interface, Route
from cyst.api.network.node import Node
from cyst.api.logic.access import Authorization, AccessLevel
from cyst.api.logic.action import Action
from cyst.api.logic.data import Data
from cyst.api.logic.exploit import VulnerableService, ExploitParameter, ExploitParameterType, ExploitLocality, ExploitCategory, Exploit
from cyst.api.network.session import Session
from cyst.api.host.service import ActiveServiceDescription, Service, PassiveService

from cyst.core.environment.message import MessageImpl, RequestImpl, ResponseImpl
from cyst.core.environment.proxy import EnvironmentProxy
from cyst.core.environment.stores import ActionStoreImpl, ServiceStoreImpl, ExploitStoreImpl
from cyst.core.host.service import ServiceImpl, PassiveServiceImpl
from cyst.core.logic.access import Policy
from cyst.core.logic.data import DataImpl
from cyst.core.logic.exploit import VulnerableServiceImpl, ExploitImpl, ExploitParameterImpl
from cyst.core.network.elements import Endpoint, Connection, InterfaceImpl, Hop, PortImpl
from cyst.core.network.network import Network
from cyst.core.network.node import NodeImpl
from cyst.core.network.router import Router
from cyst.core.network.session import SessionImpl
from cyst.api.utils.counter import Counter
from cyst.core.utils.file import root_dir


# Environment is unlike other core implementation given an underscore-prefixed name to let python complain about
# it being private if instantiated otherwise than via the create_environment()
class _Environment(Environment, EnvironmentControl, EnvironmentMessaging, EnvironmentResources, EnvironmentConfiguration,
                   NodeConfiguration, NetworkConfiguration, ServiceConfiguration, ExploitConfiguration):

    def __init__(self, pause_on_request: List[str] = None, pause_on_response: List[str] = None) -> None:
        if pause_on_request is None:
            pause_on_request = []
        if pause_on_response is None:
            pause_on_response = []

        self._network = Network()
        self._time = 0
        self._tasks = []
        self._pause = False
        self._terminate = False
        self._initialized = False
        self._state = EnvironmentState.INIT
        self._pause_on_request = pause_on_request
        self._pause_on_response = pause_on_response

        self._action_store = ActionStoreImpl()
        self._service_store = ServiceStoreImpl(self)
        self._exploit_store = ExploitStoreImpl()

        self._interpreters = {}

        self._policy = Policy()

        self._sessions_to_add = []

        self._register_services()
        self._register_actions()

    # ------------------------------------------------------------------------------------------------------------------
    # Environment. Currently everything points back to self
    @property
    def configuration(self) -> EnvironmentConfiguration:
        return self

    @property
    def control(self) -> EnvironmentControl:
        return self

    @property
    def messaging(self) -> EnvironmentMessaging:
        return self

    @property
    def resources(self) -> EnvironmentResources:
        return self

    @property
    def policy(self) -> EnvironmentPolicy:
        return self._policy

    # ------------------------------------------------------------------------------------------------------------------
    # EnvironmentMessaging
    def create_request(self, dst_ip: Union[str, IPAddress], dst_service: str = "",
                       action: Action = None, session: Session = None, authorization: Authorization = None) -> Request:
        request = RequestImpl(dst_ip, dst_service, action, session, authorization)
        return request

    def create_response(self, request: Request, status: Status, content: Optional[Any] = None, session: Optional[Session] = None, authorization: Optional[Authorization] = None) -> Response:
        # Let's abuse the duck typing and "cast" Request to RequestImpl
        if isinstance(request, RequestImpl):
            response = ResponseImpl(request, status, content, session, authorization)
            return response
        else:
            raise ValueError("Malformed request passed to create a response from")

    def send_message(self, message: MessageImpl, delay: int = 0) -> None:
        # set a first hop for a message
        source = self._network.get_node_by_id(message.origin.id)
        # Find a next hop for messages without one
        if source and not message.next_hop:
            # New request with session should follow the session first
            # Response should either follow newly established session, or route to session endpoint
            # TODO rearrange it to reflect changes in response set_next_hop handling
            if message.type == MessageType.REQUEST and message.session:
                message.set_next_hop()
                # Not a pretty thing, but I am not sure how to make it better
                it = SessionImpl.cast_from(message.session).forward_iterator
                hop = next(it)
                port = hop.src.port
                iface = source.interfaces[port]
                message.set_src_ip(iface.ip)
            elif message.type == MessageType.RESPONSE:
                if message.session and message.current == SessionImpl.cast_from(message.session).endpoint:
                    # This is stupid, but it complains...
                    if isinstance(message, ResponseImpl):
                        message.set_in_session(True)
                message.set_next_hop()
            # Others go to a gateway
            else:
                target = message.dst_ip
                gateway, port = source.gateway(target)
                if not gateway:
                    raise Exception("Could not send a message, no gateway to route it through.")

                message.set_origin(Endpoint(source.id, port))

                iface = InterfaceImpl.cast_from(source.interfaces[port])
                message.set_src_ip(iface.ip)
                # First sending is specific, because the current value is set to origin
                message.set_next_hop(message.origin, iface.endpoint)
        try:
            heappush(self._tasks, (self._time + delay, message))
        except Exception as e:
            print("Error sending a message, reason: {}".format(e))

        message.sent = True

        if message.origin.id in self._pause_on_request:
            self._pause = True

    # ------------------------------------------------------------------------------------------------------------------
    # EnvironmentControl
    @property
    def state(self):
        return self._state

    def reset(self):
        self._network.reset()
        self._time = 0
        self._tasks.clear()
        self._pause = False
        self._terminate = False
        self._state = EnvironmentState.INIT

    def _establish_sessions(self) -> None:
        for session in self._sessions_to_add:
            owner = session[0]
            waypoints = session[1]
            parent = session[2]
            service = session[3]

            # It is a questionable thing to create a deferred session and not to pass it to anyone, but in case it
            # is used/needed later, I will create it anyway
            session = self._create_session(owner, waypoints, parent)
            if service:
                node: Node
                if isinstance(waypoints[0], str):
                    node = self._network.get_node_by_id(waypoints[0])
                else:
                    node = waypoints[0]
                ServiceImpl.cast_from(node.services[service]).add_session(session)

    def init(self) -> Tuple[bool, EnvironmentState]:
        if self._initialized:
            return True, self._state

        if self._state == EnvironmentState.RUNNING or self._state == EnvironmentState.PAUSED:
            return False, self._state

        self._pause = False
        self._terminate = False
        self._state = EnvironmentState.PAUSED

        self._establish_sessions()

        self._initialized = True

        return True, self._state

    def run(self) -> Tuple[bool, EnvironmentState]:

        if not self._initialized:
            return False, self._state

        # if paused, unpause
        if self._state == EnvironmentState.PAUSED:
            self._pause = False

        # Run
        self._state = EnvironmentState.RUNNING
        self._process()

        return True, self._state

    def pause(self) -> Tuple[bool, EnvironmentState]:

        if self._state != EnvironmentState.RUNNING:
            return False, self._state

        self._pause = True
        # This will return True + running state, but it will be returned to an actor other than the one who called
        # Environment.run() in the first place. Or I hope so...
        return True, self._state

    def terminate(self) -> Tuple[bool, EnvironmentState]:

        if self._state != EnvironmentState.RUNNING:
            return False, self._state

        self._terminate = True
        return True, self._state

    def add_pause_on_request(self, id: str) -> None:
        self._pause_on_request.append(id)

    def remove_pause_on_request(self, id: str) -> None:
        self._pause_on_request = [x for x in self._pause_on_request if x != id]

    def add_pause_on_response(self, id: str) -> None:
        self._pause_on_response.append(id)

    def remove_pause_on_response(self, id: str) -> None:
        self._pause_on_response = [x for x in self._pause_on_response if x != id]

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def action_store(self) -> ActionStore:
        return self._action_store

    @property
    def service_store(self) -> ServiceStore:
        return self._service_store

    @property
    def exploit_store(self) -> ExploitStore:
        return self._exploit_store

    # ------------------------------------------------------------------------------------------------------------------
    # EnvironmentConfiguration
    # ------------------------------------------------------------------------------------------------------------------
    # Just point on itself
    @property
    def node(self) -> NodeConfiguration:
        return self

    @property
    def service(self) -> ServiceConfiguration:
        return self

    @property
    def network(self) -> NetworkConfiguration:
        return self

    @property
    def exploit(self) -> ExploitConfiguration:
        return self

    # ------------------------------------------------------------------------------------------------------------------
    # NodeConfiguration
    def create_node(self, id: str, ip: Union[str, IPAddress] = "", mask: str = "", shell: Service = None) -> Node:
        return NodeImpl(id, "Node", ip, mask, shell)

    def create_router(self, id: str, messaging: EnvironmentMessaging) -> Node:
        return Router(id, messaging)

    def create_interface(self, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0):
        return InterfaceImpl(ip, mask, index)

    def add_interface(self, node: Node, interface: Interface, index: int = -1) -> int:
        if node.type == "Router":
            return Router.cast_from(node).add_port(interface.ip, interface.mask, index)
        else:
            return NodeImpl.cast_from(node).add_interface(InterfaceImpl.cast_from(interface))

    def set_interface(self, interface: Interface, ip: Union[str, IPAddress] = "", mask: str = "") -> None:
        iface = InterfaceImpl.cast_from(interface)

        if ip:
            iface.set_ip(ip)

        if mask:
            iface.set_mask(mask)

    def add_service(self, node: Node, service: Service) -> None:
        node = NodeImpl.cast_from(node)
        service = ServiceImpl.cast_from(service)

        node.add_service(service)

    def set_shell(self, node: Node, service: Service) -> None:
        NodeImpl.cast_from(node).set_shell(service)

    def add_route(self, node: Node, route: Route) -> None:
        if node.type != "Router":
            raise RuntimeError("Attempting to add route to non-router node")

        Router.cast_from(node).add_route(route)

    def list_routes(self, node: Node) -> List[Route]:
        if node.type != "Router":
            raise RuntimeError("Attempting to add route to non-router node")

        return Router.cast_from(node).list_routes()

    # ------------------------------------------------------------------------------------------------------------------
    # ServiceConfiguration
    def create_active_service(self, id: str, owner: str, node: Node,
                              service_access_level: AccessLevel = AccessLevel.LIMITED,
                              configuration: Optional[Dict[str, Any]] = None) -> Optional[Service]:
        return self._service_store.create_active_service(id, owner, node, service_access_level, configuration)

    def create_passive_service(self, id: str, owner: str, version: str = "0.0.0", local: bool = False,
                               service_access_level: AccessLevel = AccessLevel.LIMITED) -> Service:
        return PassiveServiceImpl(id, owner, version, local, service_access_level)

    def set_service_parameter(self, service: PassiveService, parameter: ServiceParameter, value: Any) -> None:
        service = PassiveServiceImpl.cast_from(service)
        if parameter == ServiceParameter.ENABLE_SESSION:
            service.set_enable_session(value)
        elif parameter == ServiceParameter.SESSION_ACCESS_LEVEL:
            service.set_session_access_level(value)

    def create_data(self, id: Optional[str], owner: str, description: str) -> Data:
        return DataImpl(id, owner, description)

    def public_data(self, service: PassiveService) -> List[Data]:
        return PassiveServiceImpl.cast_from(service).public_data

    def private_data(self, service: PassiveService) -> List[Data]:
        return PassiveServiceImpl.cast_from(service).private_data

    def public_authorizations(self, service: PassiveService) -> List[Authorization]:
        return PassiveServiceImpl.cast_from(service).public_authorizations

    def private_authorizations(self, service: PassiveService) -> List[Authorization]:
        return PassiveServiceImpl.cast_from(service).private_authorizations

    # ------------------------------------------------------------------------------------------------------------------
    # NetworkConfiguration
    def add_node(self, node: Node) -> None:
        self._network.add_node(NodeImpl.cast_from(node))

    def add_connection(self, source: Node, target: Node, source_port_index: int = -1, target_port_index: int = -1,
                       net: str = "", connection: Connection = None) -> Connection:
        return self._network.add_connection(NodeImpl.cast_from(source), source_port_index, NodeImpl.cast_from(target), target_port_index, net, connection)

    # TODO: Decide if we want to have service association a part of the session creation, or if we rather leave it
    #       to service interface
    def create_session(self, owner: str, waypoints: List[Union[str, Node]], parent: Optional[Session] = None,
                       defer: bool = False, service: Optional[str] = None) -> Optional[Session]:

        if defer:
            self._sessions_to_add.append((owner, waypoints, parent, service))
            return None
        else:
            session = self._create_session(owner, waypoints, parent)
            if service:
                node: Node
                if isinstance(waypoints[0], str):
                    node = self._network.get_node_by_id(waypoints[0])
                else:
                    node = waypoints[0]
                ServiceImpl.cast_from(node.services[service]).add_session(session)
            return session

    def create_session_from_message(self, message: Message) -> Session:
        message = MessageImpl.cast_from(message)

        if message.authorization:
            owner = message.authorization.identity
        else:
            owner = message.dst_service
        path = message.non_session_path
        parent = message.session

        return SessionImpl(owner, parent, path, self._network)

    # ------------------------------------------------------------------------------------------------------------------
    # Exploit configuration
    def create_vulnerable_service(self, id: str, min_version: str = "0.0.0", max_version: str = "0.0.0") -> VulnerableService:
        return VulnerableServiceImpl(id, min_version, max_version)

    def create_exploit_parameter(self, exploit_type: ExploitParameterType, value: str = "",
                                 immutable: bool = False) -> ExploitParameter:
        return ExploitParameterImpl(exploit_type, value, immutable)

    def create_exploit(self, id: str = "", services: List[VulnerableService] = None, locality:
                       ExploitLocality = ExploitLocality.NONE, category: ExploitCategory = ExploitCategory.NONE,
                       *parameters: ExploitParameter) -> Exploit:
        return ExploitImpl(id, services, locality, category, *parameters)

    def add_exploit(self, *exploits: Exploit) -> None:
        self._exploit_store.add_exploit(*exploits)

    def clear_exploits(self) -> None:
        self._exploit_store.clear()

    # ------------------------------------------------------------------------------------------------------------------
    # Internal functions
    @property
    def _get_network(self) -> Network:
        return self._network

    def _create_session(self, owner: str, waypoints: List[Union[str, Node]], parent: Optional[Session]) -> Session:
        path: List[Hop] = []
        source: NodeImpl

        if len(waypoints) < 2:
            raise ValueError("The session path needs at least two ids")

        # Right now, expecting everything to be str
        last_waypoint = waypoints[0]
        if isinstance(last_waypoint, str):
            last_node = self._network.get_node_by_id(last_waypoint)
        else:
            last_node = last_waypoint
            last_waypoint = NodeImpl.cast_from(last_node).id

        path_candidates: List[List[Hop]] = []

        # Create a set of candidate hops
        for i, waypoint in enumerate(waypoints):
            # Skip the first waypoint
            if i == 0:
                continue

            if isinstance(waypoint, str):
                new_node = self._network.get_node_by_id(waypoint)
            else:
                new_node = waypoint
                waypoint = NodeImpl.cast_from(new_node).id

            for index, iface in enumerate(last_node.interfaces):
                if isinstance(iface, InterfaceImpl):
                    iface = InterfaceImpl.cast_from(iface)
                else:
                    iface = PortImpl.cast_from(iface)

                if iface.endpoint.id != waypoint:
                    continue

                hop = Hop(Endpoint(last_waypoint, index, iface.ip), iface.endpoint)

                if len(path_candidates) < i:
                    path_candidates.append([hop])
                else:
                    path_candidates[i - 1].append(hop)

            # Path candidates were not extended, give up
            if len(path_candidates) < i:
                raise RuntimeError("Could not find connection between {} and {} to establish a session".format(last_waypoint, waypoint))

            last_waypoint = waypoint
            last_node = new_node

        # Go through each hop and add only those that are linked to next hops. If there are multiple possible paths,
        # select the first viable one
        path_len = len(path_candidates)
        for i in range(0, path_len - 1):
            for element in product(path_candidates[i], path_candidates[i + 1]):
                hop_dst = NodeImpl.cast_from(self._network.get_node_by_id(element[0].dst.id))
                if (hop_dst.type == "Router" and element[0].dst.ip == element[1].src.ip) or hop_dst.type == "Node":
                    path.append(element[0])
                    if i == path_len - 2:
                        path.append(element[1])
                    break

        if path_len == 1:
            path = [path_candidates[0][0]]

        return SessionImpl(owner, parent, path, self._network)

    def _process_passive(self, message: Request, node: Node):
        time = 0
        response = None

        # TODO: In light of tags abandonment, how to deal with splitting id into namespace and action name
        if message.action.namespace in self._interpreters:
            time, response = self._interpreters[message.action.namespace].evaluate(message, node)

        return time, response

    def _send_message(self, message: MessageImpl) -> None:
        message_type = "request" if isinstance(message, Request) else "response"

        # shortcut for wakeup messages
        if message.type == MessageType.TIMEOUT:
            self._network.get_node_by_id(message.origin.id).process_message(message)
            return

        # Move message to a next hop
        message.hop()
        current_node: NodeImpl = self._network.get_node_by_id(message.current.id)

        processing_time = 0

        if current_node.type == "Router":
            result, processing_time = current_node.process_message(message)
            if result:
                heappush(self._tasks, (self._time + processing_time, message))

            return

        # Message has a session
        if message.session:
            local_processing = False
            # Message still in session, pass it along
            if message.in_session:
                message.set_next_hop()
                heappush(self._tasks, (self._time + processing_time, message))
                return
            # The session ends in the current node
            elif message.session.endpoint.id == current_node.id:
                # Check if the node is the final destination
                for iface in current_node.interfaces:
                    if iface.index == message.session.endpoint.port and iface.ip == message.dst_ip:
                        local_processing = True
                        break
                # It is not, this means the node was only a proxy to some other target
                if not local_processing:
                    # Find a way to nearest switch
                    gateway, port = current_node.gateway(message.dst_ip)
                    # ##################
                    dest_node_endpoint = current_node.interfaces[port].endpoint
                    dest_node = self._network.get_node_by_id(dest_node_endpoint.id)
                    dest_node_ip = dest_node.interfaces[dest_node_endpoint.port].ip
                    message.set_next_hop(Endpoint(current_node.id, port, current_node.interfaces[port].ip), Endpoint(dest_node_endpoint.id, dest_node_endpoint.port, dest_node_ip))
                    # ##################
                    print("Proxying {} to {} via {} on a node {}".format(message_type, message.dst_ip, message.next_hop.id, current_node.id))
                    heappush(self._tasks, (self._time + processing_time, message))
                    return

        # Message has to be processed locally
        print("Processing {} on a node {}. {}".format(message_type, current_node.id, message))

        # Service is requested
        response = None
        if message.dst_service:
            # Check if the requested service exists on the current node
            if message.dst_service not in current_node.services:
                # There is a theoretical chance for response not finding dst service for responses, if e.g. attacker
                # shut down the service after firing request and before receiving the response. In such case the
                # error is silently dropped
                if message_type == "response":
                    return

                processing_time = 1
                response = ResponseImpl(message, Status(StatusOrigin.NODE, StatusValue.ERROR), "Nonexistent service {} at node {}".format(message.dst_service, message.dst_ip))
                self.send_message(response, processing_time)

            # Service exists and it is passive
            elif current_node.services[message.dst_service].passive:
                # Passive services just discard the responses and only process the requests
                if message_type == "response":
                    return

                processing_time, response = self._process_passive(message, current_node)
                if response.status.origin == StatusOrigin.SYSTEM and response.status.value == StatusValue.ERROR:
                    print("Could not process the request, unknown semantics.")
                else:
                    self.send_message(response, processing_time)

            # Service exists and it is active
            else:
                # An active service does not necessarily produce Responses, so we should just move time
                # somehow and be done with it.
                # TODO How to move time?
                current_node.services[message.dst_service].active_service.process_message(message)

                if message_type == "response" and current_node.id + "." + message.dst_service in self._pause_on_response:
                    self._pause = True

        # If no service is specified, it is a message to a node, but still, it is processed as a request for
        # passive service and processed with the interpreter
        # No service is specified
        else:
            # If there is response arriving without destination service, just drop it
            if message_type == "response":
                return

            # If it is a request, then it is processed as a request for passive service and processed with the interpreter
            processing_time, response = self._process_passive(message, current_node)
            if response.status.origin == StatusOrigin.SYSTEM and response.status.value == StatusValue.ERROR:
                print("Could not process the request, unknown semantics.")
            else:
                self.send_message(response, processing_time)

    def _process(self) -> Tuple[bool, EnvironmentState]:

        while self._tasks and not self._pause and not self._terminate:
            next_time = self._tasks[0][0]
            delta = next_time - self._time

            # TODO singular timestep handling
            self._time = next_time

            current_tasks = []
            while self._tasks and self._tasks[0][0] == self._time:
                current_tasks.append(heappop(self._tasks)[1])

            for task in current_tasks:
                self._send_message(task)

        # Pause causes the system to stop processing and to keep task queue intact
        if self._pause:
            self._state = EnvironmentState.PAUSED

        # Terminate clears the task queue and sets the clock back to zero
        elif self._terminate:
            self._state = EnvironmentState.TERMINATED
            self._time = 0
            self._tasks.clear()

        else:
            self._state = EnvironmentState.FINISHED

        return True, self._state

    def _register_services(self) -> None:
        # Check subdirectories in the cyst/services/ directory
        path = root_dir() / 'cyst' / 'services'
        if not path.exists():
            raise RuntimeError("Cannot find 'cyst/services/' path. This indicate corruption of the simulator. Please check...")

        for x in path.iterdir():
            if x.is_dir():
                # Attempt to import main of the services and get the service descriptions
                try:
                    module_name = 'cyst.services.' + x.parts[-1] + '.main'
                    module = importlib.import_module(module_name)
                    service_description: ActiveServiceDescription = getattr(module, "service_description")

                    if self._service_store.get_service(service_description.name):
                        print("Service with name {} already registered, skipping the one in 'cyst/services/{}' directory".format(service_description.name, x.parts[-1]))
                    else:
                        self._service_store.add_service(service_description)
                except ModuleNotFoundError:
                    # Given service does not provide a main
                    print("Service {} does not provide the 'main.py' module".format(x.parts[-1]))
                    pass
                except AttributeError:
                    # Given service does not provide a service description
                    print("Service {} does not provide its description in the 'main.py' module".format(x.parts[-1]))
                    pass

    def _register_actions(self) -> None:
        # Check subdirectories in the cyst/interpreters/ directory
        path = root_dir() / 'cyst' / 'interpreters'
        if not path.exists():
            raise RuntimeError(
                "Cannot find 'cyst/interpreters/' path. This indicate corruption of the simulator. Please check...")

        for x in path.iterdir():
            if x.is_dir():
                # Attempt to import main of the interpreters and get the action interpreter descriptions
                try:
                    module_name = 'cyst.interpreters.' + x.parts[-1] + '.main'
                    module = importlib.import_module(module_name)
                    intp_description: ActionInterpreterDescription = getattr(module, "action_interpreter_description")

                    if intp_description.namespace in self._interpreters:
                        print("Action interpreter with namespace {} already registered, skipping the one in 'cyst/interpreters/{}' directory".format(intp_description.namespace, x.parts[-1]))
                    else:
                        interpreter = intp_description.creation_fn(self, self, self._policy, self)
                        self._interpreters[intp_description.namespace] = interpreter
                except ModuleNotFoundError:
                    # Given service does not provide a main
                    print("Action interpreter {} does not provide the 'main.py' module".format(x.parts[-1]))
                    pass
                except AttributeError as err:
                    # Given service does not provide a service description
                    print("Action interpreter {} does not provide its description in the 'main.py' module. Reason: {}".format(x.parts[-1], err))
                    pass

    def create_service(self, name: str, id: str, node: Node, args: Optional[Dict[str, Any]]) -> ServiceImpl:
        if name not in self._service_descriptions:
            raise AttributeError("Service '{}' not registered.".format(name))

        if not id:
            service_name = "service-" + name + "-" + str(Counter().get("services"))
        else:
            service_name = id

        proxy = EnvironmentProxy(self, NodeImpl.cast_from(node).id, service_name)

        # TODO add ownership into equation
        act = self._service_descriptions[name].creation_fn("", proxy, args)
        srv = ServiceImpl(service_name, act, name, "")

        return srv


def create_environment() -> Environment:
    e = _Environment()
    return e
