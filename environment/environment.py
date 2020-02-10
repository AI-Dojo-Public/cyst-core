from enum import Enum
from heapq import heappush, heappop
from typing import Tuple, List

from environment.message import MessageType, Request, Response, _Message, StatusValue, StatusOrigin, Status
from environment.network import Network, Connection
from environment.network_elements import Endpoint
from environment.node import Node

environment_interpreters = {}


class EnvironmentState(Enum):
    INIT = 0,
    RUNNING = 1,
    PAUSED = 2,
    FINISHED = 3,
    TERMINATED = 4


class Environment:
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
        self._state = EnvironmentState.INIT
        self._pause_on_request = pause_on_request
        self._pause_on_response = pause_on_response

    def add_node(self, node: Node) -> None:
        self._network.add_node(node)

    def add_connection(self, source: Node, target: Node, source_port_index: int = -1, target_port_index: int = -1,
                       net: str = "", connection: Connection = None) -> Connection:
        return self._network.add_connection(source, source_port_index, target, target_port_index, net, connection)

    @property
    def state(self):
        return self._state

    @property
    def network(self) -> Network:
        return self._network

    def reset(self):
        self._network.reset()
        self._time = 0
        self._tasks.clear()
        self._pause = False
        self._terminate = False
        self._state = EnvironmentState.INIT

    def _process_passive(self, message: Request, node: Node):
        time = 0
        response = None

        tags = message.action.tags
        for tag in tags:
            names = tag.name_list

            if names[0] in environment_interpreters:
                time, response = environment_interpreters[names[0]](names[1:], message, node, self)
                break

        return time, response

    def send_message(self, message: _Message, delay: int = 0) -> None:
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
                it = message.session.get_forward_iterator()
                hop = next(it)
                port = hop.src.port
                iface = source.interfaces[port]
                message.set_src_ip(iface.ip)
            elif message.type == MessageType.RESPONSE:
                if message.session and message.current == message.session.endpoint:
                    # This is stupid, but it complains...
                    if isinstance(message, Response):
                        message.set_in_session(True)
                message.set_next_hop()
            # Others go to a gateway
            else:
                target = message.dst_ip
                gateway, port = source.gateway(target)
                if not gateway:
                    raise Exception("Could not send a message, no gateway to route it through.")

                message.set_origin(Endpoint(source.id, port))

                iface = source.interfaces[port]
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

    def _send_message(self, message: _Message) -> None:
        message_type = "request" if isinstance(message, Request) else "response"

        # shortcut for wakeup messages
        if message.type == MessageType.TIMEOUT:
            self._network.get_node_by_id(message.origin.id).process_message(message)
            return

        # Move message to a next hop
        message.hop()
        current_node = self._network.get_node_by_id(message.current.id)

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
                    message.set_next_hop(Endpoint(current_node.id, port), current_node.interfaces[port].endpoint)
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
                response = Response(message, Status(StatusOrigin.NODE, StatusValue.ERROR), "Nonexistent service {} at node {}".format(message.dst_service, message.dst_ip))
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
                current_node.services[message.dst_service].process_message(message)

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

    def run(self) -> Tuple[bool, EnvironmentState]:

        if self._state == EnvironmentState.RUNNING or self._state == EnvironmentState.PAUSED:
            return False, self._state

        self._pause = False
        self._terminate = False
        self._state = EnvironmentState.RUNNING

        # This is currently disabled until I figure the best way to do an initialization of the entire simulation
        # for node in self._network.get_nodes_by_type("Attacker"):
        #     node.run()

        self._process()

        return True, self._state

    def pause(self) -> Tuple[bool, EnvironmentState]:

        if self._state != EnvironmentState.RUNNING:
            return False, self._state

        self._pause = True
        # This will return True + running state, but it will be returned to an actor other than the one who called
        # Environment.run() in the first place. Or I hope so...
        return True, self._state

    def resume(self) -> Tuple[bool, EnvironmentState]:

        if self._state != EnvironmentState.PAUSED:
            return False, self._state

        self._pause = False

        return self._process()

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


# EnvironmentProxy is a proxy for the environment, which is passed to each active node. It takes care of routing of
# messages and prevents forging of Messages and spooky action in the distance
class EnvironmentProxy:
    def __init__(self, env: Environment, node_id: str) -> None:
        self._env = env
        # Node is resolved on the first attempt to send a message
        self._node_id = node_id

    def send_request(self, request: Request, delay: int = 0) -> None:
        # Dummy origin, to make it work with Environment.send_message
        request.set_origin(Endpoint(self._node_id, -1))

        self._env.send_message(request, delay)


# This is to register all interpreters
# At the bottom to resolve cyclic import troubles
from environment.interpreter import *
