import argparse
import copy
import os
import sys

from cyst.api.environment.interpreter import ActionInterpreter

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from heapq import heappush, heappop
from itertools import product
from time import localtime
from typing import Tuple, List, Union, Optional, Any, Dict

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.environment import Environment
from cyst.api.environment.control import EnvironmentState, EnvironmentControl
from cyst.api.environment.configuration import EnvironmentConfiguration, GeneralConfiguration, NodeConfiguration, \
    ServiceConfiguration, NetworkConfiguration, ExploitConfiguration, AccessConfiguration, ActionConfiguration
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.metadata_provider import MetadataProvider
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.message import Message, MessageType, Request, StatusValue, StatusOrigin, Status, StatusDetail, Timeout
from cyst.api.logic.access import AuthenticationToken
from cyst.api.network.node import Node
from cyst.api.network.session import Session
from cyst.api.network.firewall import FirewallRule, FirewallPolicy
from cyst.api.host.service import Service, PassiveService, ActiveService, ServiceState
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.utils.counter import Counter
from cyst.api.utils.log import get_logger

from cyst.core.environment.configuration_access import AccessConfigurationImpl
from cyst.core.environment.configuration_action import ActionConfigurationImpl
from cyst.core.environment.configuration_exploit import ExploitConfigurationImpl
from cyst.core.environment.configuration_general import GeneralConfigurationImpl, RuntimeConfiguration
from cyst.core.environment.configuration_network import NetworkConfigurationImpl
from cyst.core.environment.configuration_node import NodeConfigurationImpl
from cyst.core.environment.configuration_service import ServiceConfigurationImpl
from cyst.core.environment.environment_control import EnvironmentControlImpl
from cyst.core.environment.environment_messaging import EnvironmentMessagingImpl
from cyst.core.environment.environment_resources import EnvironmentResourcesImpl
from cyst.core.environment.data_store import DataStore
from cyst.core.environment.message import MessageImpl, RequestImpl, ResponseImpl, TimeoutImpl
from cyst.core.environment.proxy import EnvironmentProxy
from cyst.core.environment.stores import ServiceStoreImpl
from cyst.core.host.service import ServiceImpl
from cyst.core.logic.access import AuthenticationTokenImpl
from cyst.core.logic.policy import Policy
from cyst.core.network.elements import Endpoint, InterfaceImpl, Hop
from cyst.core.network.firewall import service_description as firewall_service_description
from cyst.core.network.network import Network
from cyst.core.network.node import NodeImpl
from cyst.core.network.router import Router
from cyst.core.network.session import SessionImpl


# Environment is unlike other core implementation given an underscore-prefixed name to let python complain about
# it being private if instantiated otherwise than via the create_environment()
class _Environment(Environment, EnvironmentConfiguration):

    def __init__(self) -> None:
        self._time = 0
        self._start_time = localtime()
        self._tasks: List[Tuple[int, int, MessageImpl]] = []
        self._pause = False
        self._terminate = False
        self._initialized = False
        self._state = EnvironmentState.INIT

        self._run_id = ""

        self._pause_on_request: List[str] = []
        self._pause_on_response: List[str] = []

        # Interface implementations
        self._environment_control = EnvironmentControlImpl(self)
        self._environment_messaging = EnvironmentMessagingImpl(self)
        self._environment_resources = EnvironmentResourcesImpl(self)

        self._service_store = ServiceStoreImpl(self.messaging, self.resources)

        self._interpreters: Dict[str, ActionInterpreter] = {}
        # TODO currently, there can be only on metadata provider for one namespace
        self._metadata_providers: Dict[str, MetadataProvider] = {}

        self._policy = Policy(self)

        self._sessions_to_add: List[Tuple[ str, List[Union[str, Node]],Optional[str] ,Optional[str], Optional[Session], bool]] = []

        self._access_configuration = AccessConfigurationImpl(self)
        self._action_configuration = ActionConfigurationImpl(self)
        self._exploit_configuration = ExploitConfigurationImpl(self)
        self._general_configuration = GeneralConfigurationImpl(self)
        self._network_configuration = NetworkConfigurationImpl(self)
        self._node_configuration = NodeConfigurationImpl(self)
        self._service_configuration = ServiceConfigurationImpl(self)
        self._runtime_configuration = RuntimeConfiguration()

        self._configure_runtime()
        self._register_services()
        self._register_actions()
        self._register_metadata_providers()

        self._network = Network(self._general_configuration)

        self._data_store = DataStore(self._runtime_configuration.data_backend,
                                     self._runtime_configuration.data_backend_params)

        # Logs
        self._message_log = get_logger("messaging")

    def __getstate__(self) -> dict:
        return {
            # Simple values
            "_time": self._time,
            "_start_time": self._start_time,
            "_pause": self._pause,
            "_terminate": self._terminate,
            "_initialized": self._initialized,
            "_state": self._state,
            "_run_id": self._run_id,

            # Arrays
            "_pause_on_response": self._pause_on_response,
            "_pause_on_request": self._pause_on_request,

            # Simple objects
            "_runtime_configuration": self._runtime_configuration,

            # Complex beasts
            "_service_store": self._service_store,
            "_environment_resources": self._environment_resources,
            "_metadata_providers": self._metadata_providers,
            "_network": self._network,
            "_general_configuration": self._general_configuration

            # Ignored members
            # Policy - is reinitialized, no need to serialize
            # DataStore - stays the same across serializations
            # Log - stays the same across serializations
            # All interface implementations excluding the general configuration and environment resources
        }

    def __setstate__(self, state: dict) -> None:
        self._time = state["_time"]
        self._start_time = state["_start_time"]
        self._pause = state["_pause"]
        self._terminate = state["_terminate"]
        self._initialized = state["_initialized"]
        self._state = state["_state"]
        self._run_id = state["_run_id"]

        self._pause_on_response = state["_pause_on_response"]
        self._pause_on_request = state["_pause_on_request"]

        self._runtime_configuration = state["_runtime_configuration"]

        self._service_store = state["_service_store"]
        self._environment_resources = state["_environment_resources"]
        self._metadata_providers = state["_metadata_providers"]
        self._network = state["_network"]
        self._general_configuration = state["_general_configuration"]

        # Members reconstructed on the fly
        self._policy = Policy(self)

        self._environment_control = EnvironmentControlImpl(self)
        self._environment_messaging = EnvironmentMessagingImpl(self)

        self._access_configuration = AccessConfigurationImpl(self)
        self._action_configuration = ActionConfigurationImpl(self)
        self._exploit_configuration = ExploitConfigurationImpl(self)
        self._network_configuration = NetworkConfigurationImpl(self)
        self._node_configuration = NodeConfigurationImpl(self)
        self._service_configuration = ServiceConfigurationImpl(self)

    # Replace the environment with the state of another environment. This is used for deserialization. It is explicit to
    # avoid replacing of ephemeral stuff, such as data store connections or whatnot
    def _replace(self, env: "_Environment"):
        self._time = env._time
        self._start_time = env._start_time
        self._pause = env._pause
        self._terminate = env._terminate
        self._initialized = env._initialized
        self._state = env._state
        self._run_id = env._run_id

        self._pause_on_response = env._pause_on_response
        self._pause_on_request = env._pause_on_request

        self._runtime_configuration = env._runtime_configuration

        self._service_store = env._service_store
        self._environment_resources = env._environment_resources
        self._metadata_providers = env._metadata_providers
        self._network = env._network
        self._general_configuration = env._general_configuration

        self._policy = env._policy

    # Runtime parameters can be passed via command-line, configuration file, or through environment variables
    # In case of multiple definitions of one parameter, the order is, from the most important to least:
    #                                                            command line, configuration file, environment variables
    def _configure_runtime(self) -> None:
        # Environment
        data_backend = os.environ.get('CYST_DATA_BACKEND')
        data_backend_params: Dict[str, str] = dict()
        if data_backend:
            data_backend_params_serialized = os.environ.get('CYST_DATA_BACKEND_PARAMS')
            # we expect parameters to be given in the form "param1_name","param1_value","param2_name","param2_value",...
            if data_backend_params_serialized:
                data_backend_params = dict(tuple(x) for x in data_backend_params_serialized.split(',').islice(2))
        run_id = os.environ.get('CYST_RUN_ID')
        config_id = os.environ.get('CYST_CONFIG_ID')
        config_filename = os.environ.get('CYST_CONFIG_FILENAME')

        # Command line (only parsing)
        cmdline_parser = argparse.ArgumentParser(description="CYST runtime configuration")

        cmdline_parser.add_argument("-c", "--config_file", type=str,
                                    help="Path to a file storing the configuration. Commandline overrides the items in configuration file.")
        cmdline_parser.add_argument("-b", "--data_backend", type=str,
                                    help="The type of a backend to use. Currently supported are: REDIS")
        cmdline_parser.add_argument("-p", "--data_backend_parameter", action="append", nargs=2, type=str,
                                    metavar=('NAME', 'VALUE'), help="Parameters to be passed to data backend.")
        cmdline_parser.add_argument("-r", "--run_id", type=str,
                                    help="A unique identifier of a simulation run. If not specified, a UUID will be generated instead.")
        cmdline_parser.add_argument("-i", "--config_id", type=str,
                                    help="A unique identifier of simulation run configuration, which can be obtained from the data store.")

        args, _ = cmdline_parser.parse_known_args()
        if args.config_file:
            config_filename = args.config_file

        # --------------------------------------------------------------------------------------------------------------
        # Config file TODO
        if config_filename:
            pass
        # --------------------------------------------------------------------------------------------------------------

        # Command line argument override
        if args.data_backend:
            data_backend = args.data_backend

        if args.data_backend_parameter:
            # Convert from list of lists into a list of tuples
            data_backend_params = dict(tuple(x) for x in args.data_backend_parameter) #MYPY: typehinting lambda not really possible this way, better to ignore?

        if args.run_id:
            run_id = args.run_id

        if args.config_id:
            config_id = args.config_id

        # --------------------------------------------------------------------------------------------------------------
        if data_backend:  # Fuck, I miss oneliners
            self._runtime_configuration.data_backend = data_backend
        if data_backend_params:
            self._runtime_configuration.data_backend_params = data_backend_params
        if config_filename:
            self._runtime_configuration.config_filename = config_filename
        if run_id:
            self._runtime_configuration.run_id = run_id
        if config_id:
            self._runtime_configuration.config_id = config_id

    # ------------------------------------------------------------------------------------------------------------------
    # Environment.
    @property
    def configuration(self) -> EnvironmentConfiguration:
        return self

    @property
    def control(self) -> EnvironmentControl:
        return self._environment_control

    @property
    def messaging(self) -> EnvironmentMessaging:
        return self._environment_messaging

    @property
    def resources(self) -> EnvironmentResources:
        return self._environment_resources

    @property
    def policy(self) -> EnvironmentPolicy:
        return self._policy

    def configure(self, *config_item: ConfigItem) -> Environment:
        return self._general_configuration.configure(*[copy.deepcopy(x) for x in config_item])

    # ------------------------------------------------------------------------------------------------------------------
    # EnvironmentConfiguration
    # ------------------------------------------------------------------------------------------------------------------
    # Just point on itself
    @property
    def general(self) -> GeneralConfiguration:
        return self._general_configuration

    @property
    def node(self) -> NodeConfiguration:
        return self._node_configuration

    @property
    def service(self) -> ServiceConfiguration:
        return self._service_configuration

    @property
    def network(self) -> NetworkConfiguration:
        return self._network_configuration

    @property
    def exploit(self) -> ExploitConfiguration:
        return self._exploit_configuration

    @property
    def action(self) -> ActionConfiguration:
        return self._action_configuration

    @property
    def access(self) -> AccessConfiguration:
        return self._access_configuration

    # ------------------------------------------------------------------------------------------------------------------
    # Internal functions
    @property
    def _get_network(self) -> Network:
        return self._network

    # When creating sessions from nodes, there are two options - either nodes are connected directly, or they
    # go through a router. So correct hops are evaluated either in N-R*-N form or N-N
    # TODO: If one direction fails, session should try constructing itself in reverse order and then restructure hops
    #       so that the origin is always at the first waypoint.
    def _create_session(self, owner: str, waypoints: List[Union[str, Node]], src_service: Optional[str],
                        dst_service: Optional[str], parent: Optional[Session], reverse: bool) -> Session:
        path: List[Hop] = []
        source: NodeImpl
        session_reversed = False

        if len(waypoints) < 2:
            raise ValueError("The session path needs at least two ids")

        session_constructed = True
        for direction in ("forward", "reverse"):

            if direction == "reverse":
                if not session_constructed:
                    path.clear()
                    waypoints.reverse()
                    session_reversed = True
                    session_constructed = True
                else:
                    break

            i = 0
            while i < len(waypoints) - 1:
                # There was an error in partial session construction
                if not session_constructed:
                    break

                node0 = None
                node1 = None
                node2 = None

                def get_node_from_waypoint(self, i: int) -> Node:
                    if isinstance(waypoints[i], str):
                        node = self._network.get_node_by_id(waypoints[i])
                    else:
                        node = waypoints[i]
                    return node

                # Get the nodes
                node0 = get_node_from_waypoint(self, i)
                node1 = get_node_from_waypoint(self, i + 1)

                routers = []
                # N-R*-N
                if node1.type == "Router":
                    router = Router.cast_from(node1)

                    routers.append(router)
                    node2 = get_node_from_waypoint(self, i + len(routers) + 1)

                    while node2.type == "Router":
                        routers.append(Router.cast_from(node2))
                        node2 = get_node_from_waypoint(self, i + len(routers) + 1)


                    path_candidate: List[Hop] = []
                    for elements in product(node0.interfaces, node2.interfaces):
                        node0_iface = InterfaceImpl.cast_from(elements[0])
                        node2_iface = InterfaceImpl.cast_from(elements[1])

                        path_candidate.clear()

                        # Check if the next router is connected to the first node
                        if node0_iface.endpoint.id != routers[0].id:
                            continue

                        # It is, so it's a first hop
                        path_candidate.append(
                            Hop(Endpoint(NodeImpl.cast_from(node0).id, node0_iface.index, node0_iface.ip),
                                node0_iface.endpoint))

                        # Check for every router if it routes the source and destination
                        for j, r in enumerate(routers):
                            # Find if there is a forward port
                            # Ports are returned in order of priority: local IPs, remote IPs sorted by specificity (CIDR)
                            port = r.routes(node0_iface.ip, node2_iface.ip, "*")

                            # No suitable port found, try again
                            if not port:
                                break

                            path_candidate.append(Hop(Endpoint(r.id, port.index, port.ip), port.endpoint))

                        if len(path_candidate) == len(routers) + 1:
                            path.extend(path_candidate)
                            break

                    i += len(routers) + 1

                    if len(path) < i:
                        session_constructed = False
                        break
                        # raise RuntimeError("Could not find connection between {} and {} to establish a session".format(NodeImpl.cast_from(node0).id, NodeImpl.cast_from(node2).id))
                else:
                    # N-N
                    for iface in node0.interfaces:
                        node0_iface = InterfaceImpl.cast_from(iface)

                        if node0_iface.endpoint.id == NodeImpl.cast_from(node1).id:
                            path.append(Hop(Endpoint(NodeImpl.cast_from(node0).id, node0_iface.index, node0_iface.ip),
                                            node0_iface.endpoint))
                            break

                    i += 1
                    if len(path) < i:
                        session_constructed = False
                        break
                        # raise RuntimeError("Could not find connection between {} and {} to establish a session".format(NodeImpl.cast_from(node0).id, NodeImpl.cast_from(node1).id))

        if not session_constructed:
            # Sessions are always tried to be constructed in both directions, so we need to reverse the waypoints again
            waypoints.reverse()
            raise RuntimeError(
                "Could not find connection between the following waypoints to establish a session".format(waypoints)) #MYPY: Missing the parameter in string

        # If the session was constructed from the end to front, we need to reverse the path
        if session_reversed:
            path.reverse()
            for i in range(0, len(path)):
                path[i] = path[i].swap()

        return SessionImpl(owner, parent, path, src_service, dst_service, self._network) #MYPY: Services can be None, they are optional

    def _process_passive(self, message: Request, node: Node):
        time = 0
        response = None

        message = RequestImpl.cast_from(message)

        # TODO: auto-authentication here, maybe??
        # cyst namespace is currently disabled from auto authentication
        if message.auth and isinstance(message.auth, AuthenticationToken):
            if not AuthenticationTokenImpl.is_local_instance(message.auth):
                return time, self.messaging.create_response(message, Status(StatusOrigin.SERVICE,
                                                                            StatusValue.FAILURE,
                                                                            StatusDetail.AUTHENTICATION_NOT_APPLICABLE),
                                                            "Auto-authentication does not work with non-local tokens",
                                                            session=message.session, auth=message.auth) #MYPY: AuthenticationToken is not valid type here. Depends, if they were just forgotten in annotation or not
            # TODO: assess if locality check makes sense
            original_action = message.action
            auth_action = self._environment_resources.action_store.get("meta:authenticate").copy()
            auth_action.parameters["auth_token"].value = message.auth
            message.action = auth_action  # swap to authentication
            auth_time, auth_response = self._interpreters["meta"].evaluate(message, node)

            if auth_response.status.value == StatusValue.FAILURE:  # not authorized
                return auth_time, auth_response

            message.auth = auth_response.auth  # if authentication successful, swap auth token for authorization
            message.action = original_action  # swap back original action
        #  and continue to action

        # TODO: In light of tags abandonment, how to deal with splitting id into namespace and action name
        if message.action.namespace in self._interpreters:
            time, response = self._interpreters[message.action.namespace].evaluate(message, node)

        return time, response

    def _send_message(self, message: MessageImpl) -> None:
        message_type = "request" if isinstance(message, Request) else "response"

        # shortcut for wakeup messages
        if message.type == MessageType.TIMEOUT:
            self._network.get_node_by_id(message.origin.id).process_message(message)  #MYPY: Node returned by get_node can be None
            return

        # Store it into the history
        self._data_store.set(self._run_id, message, Message)

        # Move message to a next hop
        message.hop()
        current_node: NodeImpl = self._network.get_node_by_id(message.current.id) #MYPY: Get node can return None

        connection = self.configuration.network.get_connections(current_node, message.current.port)[0]
        delay, result = connection.evaluate(message)
        if delay < 0:
            # TODO: message dropped, what to do? Maybe send early without processing
            pass

        message = MessageImpl.cast_from(result)
        processing_time = max(0, delay)

    # HACK: Because we want to enable actions to be able to target routers, we need to bypass the router processing
        #       if the message is at the end of its journey
        last_hop = message.dst_ip == message.current.ip #MYPY: current can return None

        if not last_hop and current_node.type == "Router":
            result, delay = current_node.process_message(message) #MYPY: This only returns one int, will crash
            processing_time += delay
            if result:
                heappush(self._tasks, (self._time + processing_time, Counter().get("msg"), message))

            return

        # Message has a session
        if message.session:
            local_processing = False
            # Message still in session, pass it along
            if message.in_session:
                message.set_next_hop()
                heappush(self._tasks, (self._time + processing_time, Counter().get("msg"), message))
                return
            # The session ends in the current node
            elif message.session.endpoint.id == current_node.id or message.session.startpoint.id == current_node.id:  #MYPY: here on multiple line, session only has an end and start, not endpoint and startpoint
                # TODO bi-directional session complicate the situation soooo much
                end_port = None
                if message.session.endpoint.id == current_node.id:
                    end_port = message.session.endpoint.port
                elif message.session.startpoint.id == current_node.id:
                    end_port = message.session.startpoint.port

                # Check if the node is the final destination
                for iface in current_node.interfaces:
                    if iface.index == end_port and iface.ip == message.dst_ip: #MYPY: Interface does not have index
                        local_processing = True
                        break
                # It is not, this means the node was only a proxy to some other target
                if not local_processing:
                    # Find a way to nearest switch
                    gateway, port = current_node.gateway(message.dst_ip) #MYPY: If this returns None, there is only one value and it will crash on unpacking it
                    # ##################
                    dest_node_endpoint = current_node.interfaces[port].endpoint #MYPY: end vs endpoint
                    dest_node = self._network.get_node_by_id(dest_node_endpoint.id)
                    dest_node_ip = dest_node.interfaces[dest_node_endpoint.port].ip #MYPY: dest_node can be None
                    message.set_next_hop(Endpoint(current_node.id, port, current_node.interfaces[port].ip),
                                         Endpoint(dest_node_endpoint.id, dest_node_endpoint.port, dest_node_ip))
                    # ##################
                    self._message_log.debug(
                        f"Proxying {message_type} to {message.dst_ip} via {message.next_hop.id} on a node {current_node.id}")
                    heappush(self._tasks, (self._time + processing_time, Counter().get("msg"), message))
                    return

        # Message has to be processed locally
        self._message_log.debug(f"Processing {message_type} on a node {current_node.id}. {message}")

        # Before a message reaches to services within, it is evaluated by all traffic processors
        # While they are returning true, everything is ok. Once they return false, the message processing stops
        # Traffic processors are free to send any reply as they see fit
        # TODO: Firewall does not return a response and currently we want it in some instances to return it and in
        #       some instances we don't. This is not a good situation.
        for processor in current_node.traffic_processors:
            result, delay = processor.process_message(message)
            if not result:
                return

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

                processing_time += 1
                response = ResponseImpl(message, Status(StatusOrigin.NODE, StatusValue.ERROR),
                                        "Nonexistent service {} at node {}".format(message.dst_service, message.dst_ip),
                                        session=message.session, auth=message.auth)
                self._environment_messaging.send_message(response, processing_time)

            # Service exists and it is passive
            elif current_node.services[message.dst_service].passive:  #MYPY: passive vs .passive_service
                # Passive services just discard the responses and only process the requests
                if message_type == "response":
                    return

                if current_node.services[message.dst_service].passive_service.state != ServiceState.RUNNING:
                    response = ResponseImpl(message, Status(StatusOrigin.NODE, StatusValue.ERROR),
                                            "Service {} at node {} is not running".format(message.dst_service, message.dst_ip),
                                            session=message.session, auth=message.auth)
                    self._environment_messaging.send_message(response, processing_time)
                else:
                    delay, response = self._process_passive(message, current_node)
                    processing_time += delay
                    if response.status.origin == StatusOrigin.SYSTEM and response.status.value == StatusValue.ERROR:
                        print("Could not process the request, unknown semantics.")
                    else:
                        self._environment_messaging.send_message(response, processing_time)
            # Service exists and it is active
            else:
                # An active service does not necessarily produce Responses, so we should just move time
                # somehow and be done with it.
                # TODO How to move time?

                # The response is reaching its destination. If it is a part of a composite action, we defer the
                # processing to the composite action manager.
                # Logic:
                # - if message.is_composite_action_chain:
                #     # CompositeActionManager swallows messages belonging to the chain and only returns a processable
                #     # message after the final action is done or irrecoverable error is encountered
                #     message = CompositeActionManager.process(message)
                #
                #   if message:
                #        active_service.process_message()

                result, delay = current_node.services[message.dst_service].active_service.process_message(message)

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
            delay, response = self._process_passive(message, current_node) #MYPY: messageimpl vs request
            processing_time += delay
            if response.status.origin == StatusOrigin.SYSTEM and response.status.value == StatusValue.ERROR: #MYPY: same as above, response None?
                print("Could not process the request, unknown semantics.")
            else:
                self._environment_messaging.send_message(response, processing_time)

    def _process(self) -> Tuple[bool, EnvironmentState]:

        while self._tasks and not self._pause and not self._terminate:
            next_time = self._tasks[0][0]
            delta = next_time - self._time

            # TODO singular timestep handling
            self._time = next_time

            current_tasks: List[MessageImpl] = []
            while self._tasks and self._tasks[0][0] == self._time:
                current_tasks.append(heappop(self._tasks)[2])

            for task in current_tasks:
                if task.type == MessageType.TIMEOUT:
                    # Yay!
                    timeout = TimeoutImpl.cast_from(task.cast_to(Timeout)) #type:ignore #MYPY: Probably an issue with mypy, requires creation of helper class
                    timeout.service.process_message(task)
                else:
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

        # First, check entry points registered via the importlib mechanism
        plugin_services = entry_points(group="cyst.services")
        for s in plugin_services:
            service_description = s.load()

            if self._service_store.get_service(service_description.name):
                print("Service with name {} already registered, skipping...".format(service_description.name))
            else:
                self._service_store.add_service(service_description)

        # Explicit addition of built-in active services
        self._service_store.add_service(firewall_service_description)

    def _register_actions(self) -> None:

        plugin_models = entry_points(group="cyst.models")
        for s in plugin_models:
            model_description = s.load()

            if model_description.namespace in self._interpreters:
                print("Behavioral model with namespace {} already registered, skipping it ...".format(
                    model_description.namespace))
            else:
                model = model_description.creation_fn(self, self._environment_resources, self._policy,
                                                      self._environment_messaging)
                self._interpreters[model_description.namespace] = model

    def _register_metadata_providers(self) -> None:

        plugin_providers = entry_points(group="cyst.metadata_providers")
        for s in plugin_providers:
            provider_description = s.load()

            if provider_description.namespace in self._metadata_providers:
                print("Metadata provider with namespace {} already registered, skipping ...".format(
                    provider_description.namespace))
            else:
                provider = provider_description.creation_fn(self._environment_resources.action_store, self)
                self._metadata_providers[provider_description.namespace] = provider
                provider.register_action_parameters()


def create_environment() -> Environment:
    e = _Environment()
    return e
