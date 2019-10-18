from enum import Enum
from heapq import heappush, heappop
from typing import Tuple, List

from environment.message import MessageType, Ack, Request, Response, Message
from environment.network import Network, Connection, Switch
from environment.node import PassiveNode, Node

environment_interpreters = {}

# This is to register all interpreters
from environment.interpreter import *


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

    def add_connection(self, source: Node, target: Node, connection: Connection = None) -> None:
        self._network.add_connection(source, target, connection)

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

    def _process_passive(self, message: Request, node: PassiveNode):
        time = 0
        response = None

        tags = message.action.tags
        for tag in tags:
            names = tag.name_list

            if names[0] in environment_interpreters:
                time, response = environment_interpreters[names[0]](names[1:], message, node)
                break

        return time, response

    def send_message(self, message: Message, delay: int = 0) -> None:
        # set a first hop for a message
        source = self._network.get_node_by_ip(message.source)
        # Messages that are originating from switch have their first hop already set
        if source and not isinstance(source, Switch):
            message.set_next_hop(source.gateway)

        heappush(self._tasks, (self._time + delay, message))

        if message.source in self._pause_on_request:
            self._pause = True

    def _send_message(self, message: Message) -> None:

        # shortcut for wakeup messages
        if message.type == MessageType.TIMEOUT:
            self._network.get_node_by_ip(message.source).process_message(message)
            return

        current_node = self._network.get_node_by_ip(message.current)

        # Ack for successfully sending a message
        if current_node and not isinstance(current_node, PassiveNode):
            current_node.process_message(Ack(message.id))

        # Move message to a next hop
        message.hop()
        current_node = self._network.get_node_by_ip(message.current)

        processing_time = 0
        # If the node is passive, let the environment process it
        if isinstance(current_node, PassiveNode):
            # Responses are silently ignored, because there is currently no semantics for processing
            # responses traversing passive nodes
            if isinstance(message, Request):
                print("Processing request on passive node {}. {}".format(current_node.id, message))
                processing_time, response = self._process_passive(message, current_node)
                if not response:
                    print("Could not process the request, unknown semantics.")
                else:
                    self.send_message(response, processing_time)
        else:
            result, processing_time = current_node.process_message(message)

            if not result:
                return

            # Only active nodes can be source of a pause and pause is not triggered by Ack message
            if current_node.id in self._pause_on_response:
                self._pause = True

        if message.current != message.target:
            heappush(self._tasks, (self._time + processing_time, message))

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
