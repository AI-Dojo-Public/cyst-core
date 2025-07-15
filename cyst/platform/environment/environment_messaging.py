from __future__ import annotations

from heapq import heappush
from netaddr import IPAddress
from typing import TYPE_CHECKING, Optional, Any, Union, Dict, List

from cyst.api.environment.message import Request, Response, Status, Message, StatusValue, StatusOrigin, ComponentState, \
    Signal
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.host.service import ServiceState
from cyst.api.logic.access import Authorization, AuthenticationTarget, AuthenticationToken
from cyst.api.logic.action import Action, ActionType
from cyst.api.logic.metadata import Metadata
from cyst.api.network.firewall import Firewall
from cyst.api.network.session import Session
from cyst.api.utils.counter import Counter
from cyst.api.utils.duration import msecs

from cyst.platform.environment.message import RequestImpl, ResponseImpl, MessageImpl, MessageType
from cyst.platform.host.service import ServiceImpl
# from cyst.platform.logic.action import ActionImpl
from cyst.platform.network.elements import Endpoint, InterfaceImpl
from cyst.platform.network.node import NodeImpl
from cyst.platform.network.session import SessionImpl

if TYPE_CHECKING:
    from cyst.platform.main import CYSTPlatform

class EnvironmentMessagingImpl(EnvironmentMessaging):
    def __init__(self, platform: CYSTPlatform):
        self._platform = platform

    def send_message(self, message: Message, delay: float = 0.0) -> None:
        # Messages with composite actions need to be processed via ActionManager
        # Logic:
        # if message.action.is_composite_action:
        #    self._env.composite_action_manager.process_composite_action(message)
        # else:
        #    # the rest
        m = MessageImpl.cast_from(message)
        _send_message(self._platform, m, delay)

    def create_request(self, dst_ip: Union[str, IPAddress], dst_service: str = "", action: Optional[Action] = None,
                       session: Optional[Session] = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None,
                       original_request: Optional[Request] = None) -> Request:
        return RequestImpl(dst_ip, dst_service, action, session, auth, original_request)

    def create_response(self, request: Request, status: Status, content: Optional[Any] = None,
                        session: Optional[Session] = None,
                        auth: Optional[Union[Authorization, AuthenticationTarget]] = None,
                        original_response: Optional[Response] = None):
        # Let's abuse the duck typing and "cast" Request to RequestImpl
        if isinstance(request, RequestImpl):
            response = ResponseImpl(request, status, content, session, auth, original_response)
            return response
        else:
            raise ValueError("Malformed request passed to create a response from")

    def create_signal(self, signal_origin: str, state: ComponentState, effect_origin: str,
                      effect_message: Optional[int] = None, effect_description: str = "",
                      effect_parameters: Optional[Dict[str, Any]] = None) -> Signal:
        # There is no reason to not use CYST's machinery
        return self._platform.messaging.create_signal(signal_origin, state, effect_origin, effect_message,
                                                      effect_description, effect_parameters)

    def open_session(self, request: Request, reverse_direction: bool = False) -> Session:
        return _open_session(self._platform, request, reverse_direction)

    async def message_hop(self, message: Message) -> None:
        await _message_hop(self._platform, message)

    async def message_process(self, message: Message) -> None:
        await _message_process(self._platform, message)

# ----------------------------------------------------------------------------------------------------------------------
# Free function implementations of the above class. It is being done this way to shut up the type checking and to
# overcome python's limitation on having a class implemented in multiple files.
def _open_session(self: CYSTPlatform, message: Message, reverse_direction: bool) -> Session:
    return self._network_configuration.create_session_from_message(message, reverse_direction)


def extract_metadata_action(action: Action, action_list: List[Action]):
    if not action.components:
        action_list.append(action)
    else:
        for c in action.components:
            extract_metadata_action(c, action_list)


def _send_message(self: CYSTPlatform, message: MessageImpl, delay: float = 0.0) -> None:
    # Shortcut for timeout
    if message.type == MessageType.TIMEOUT:
        heappush(self._message_queue, (self._time + delay, Counter().get("msg"), message))
        return

    if message.type == MessageType.REQUEST:
        # Set origin ID from platform-specific info
        caller_id: str = message.platform_specific["caller_id"]
        node_id, service_id = caller_id.split(".")

        message.set_origin(Endpoint(node_id, -1))
        message.src_service = service_id

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
            # it = SessionImpl.cast_from(message.session).forward_iterator
            # hop = next(it)
            # port = hop.src.port
            # iface = source.interfaces[port]

            # If this works it is a proof that the entire routing must be reviewed
            message.set_src_ip(message.path[0].src.ip)
        elif message.type == MessageType.RESPONSE:
            if message.session and message.current == SessionImpl.cast_from(message.session).endpoint:
                # This is stupid, but it complains...
                if isinstance(message, ResponseImpl):
                    message.set_in_session(True)
            message.set_next_hop()
        # Others go to a gateway
        else:
            target = message.dst_ip
            localhost = IPAddress("127.0.0.1")

            # Shortcut for localhost request
            if target == localhost:
                message.set_src_ip(localhost)
                message.set_next_hop(Endpoint(message.origin.id, 0, localhost), Endpoint(message.origin.id, 0, localhost))

            else:
                gateway, port = source.gateway(target)
                if not gateway:
                    raise Exception("Could not send a message, no gateway to route it through.")

                iface = InterfaceImpl.cast_from(source.interfaces[port])
                message.set_src_ip(iface.ip)

                message.set_origin(Endpoint(source.id, port, iface.ip))

                # First sending is specific, because the current value is set to origin
                message.set_next_hop(message.origin, iface.endpoint)

    try:
        heappush(self._message_queue, (self._time + delay, Counter().get("msg"), message))
    except Exception as e:
        self._message_log.error(f"Error sending a message, reason: {e}")

# TODO: Time handling is still completely bonkers. If I send a message at time X and it should arrive at router at X+1
#       then any router responses are sent as from time X (log-wise).
async def _message_hop(self: CYSTPlatform, message: Message) -> None:
    message = MessageImpl.cast_from(message)

    # This is just for log messages
    message_type = str(message.type.name).lower()

    # Special processing on the first hop
    if not message.sent:
        message.sent = True
        self._message_log.debug(f"Sending a message: {str(message)}")

    # shortcut for wakeup messages
    # TODO: Commented out (origin may be problematic if not via send_message)
    # if message.type == MessageType.TIMEOUT:
    #     self._network.get_node_by_id(message.origin.id).process_message(message)  # MYPY: Node returned by get_node can be None
    #     return

    # Traffic processor are affecting request before they are even sent out (not on routers, as that would double
    # the processing)
    if message.type == MessageType.REQUEST:
        current_node: NodeImpl = self._network.get_node_by_id(message.current.id)
        if current_node.type != "Router":
            for processor in current_node.traffic_processors:
                result, delay = await processor.process_message(message)
                if not result:
                    return

    # Store it into the history
    # Move platform-specific-and-data-store-worthy information into the platform_specific attribute
    message.platform_specific["current_hop_ip"] = str(message.current.ip)
    message.platform_specific["current_hop_id"] = message.current.id
    message.platform_specific["next_hop_ip"] = str(message.next_hop.ip)
    message.platform_specific["next_hop_id"] = message.next_hop.id

    self._infrastructure.data_store.add_message(message)

    # Move message to a next hop
    message.hop()
    current_node: NodeImpl = self._network.get_node_by_id(message.current.id)  # MYPY: Get node can return None

    # If the message was not running around localhost, get the connection delay
    delay = 0
    if message.src_ip != message.dst_ip:
        connection = self.configuration.network.get_connections(current_node, message.current.port)[0]
        delay, result = connection.evaluate(message)
        if delay < 0:
            # TODO: message dropped, what to do? Maybe send early without processing
            pass

    message = MessageImpl.cast_from(message)
    # TODO: Parametrization of platform should be in one place and not be magic constants everywhere
    processing_time = max(msecs(20).to_float(), delay)

    # HACK: Because we want to enable actions to be able to target routers, we need to bypass the router processing
    #       if the message is at the end of its journey
    last_hop = message.dst_ip == message.current.ip  # MYPY: current can return None

    if not last_hop and current_node.type == "Router":
        result, delay = await current_node.process_message(message, processing_time)
        processing_time += delay
        if result:
            heappush(self._message_queue, (self._time + processing_time, Counter().get("msg"), message))

        return

    # Message has a session
    if message.session:
        local_processing = False
        # Message still in session, pass it along
        if message.in_session:
            message.set_next_hop()
            heappush(self._message_queue, (self._time + processing_time, Counter().get("msg"), message))
            return
        # The session ends in the current node
        elif message.session.endpoint.id == current_node.id or message.session.startpoint.id == current_node.id:  # MYPY: here on multiple line, session only has an end and start, not endpoint and startpoint
            # TODO bi-directional session complicate the situation soooo much
            end_port = None
            if message.session.endpoint.id == current_node.id:
                end_port = message.session.endpoint.port
            elif message.session.startpoint.id == current_node.id:
                end_port = message.session.startpoint.port

            # Check if the node is the final destination
            for iface in current_node.interfaces:
                if iface.index == end_port and iface.ip == message.dst_ip:  # MYPY: Interface does not have index
                    local_processing = True
                    break
            # It is not, this means the node was only a proxy to some other target
            if not local_processing:
                # Find a way to nearest switch
                gateway, port = current_node.gateway(message.dst_ip)  # MYPY: If this returns None, there is only one value and it will crash on unpacking it
                # ##################
                dest_node_endpoint = current_node.interfaces[port].endpoint  # MYPY: end vs endpoint
                dest_node = self._network.get_node_by_id(dest_node_endpoint.id)
                dest_node_ip = dest_node.interfaces[dest_node_endpoint.port].ip  # MYPY: dest_node can be None
                message.set_next_hop(Endpoint(current_node.id, port, current_node.interfaces[port].ip),
                                     Endpoint(dest_node_endpoint.id, dest_node_endpoint.port, dest_node_ip))
                # ##################
                self._message_log.debug(
                    f"Proxying a {message_type} to {message.dst_ip} via {message.next_hop.id} on a node {current_node.id}")
                heappush(self._message_queue, (self._time + processing_time, Counter().get("msg"), message))
                return

    # Message has to be processed locally
    heappush(self._execute_queue, (self._time + processing_time, Counter().get("msg"), message))


async def _message_process(self: CYSTPlatform, message: Message) -> None:
    message = MessageImpl.cast_from(message)
    processing_time = 0

    # This is just for log messages
    message_type = str(message.type.name).lower()
    current_node: NodeImpl = self._network.get_node_by_id(message.current.id)  # MYPY: Get node can return None

    self._message_log.debug(f"Processing a {message_type} on a node {current_node.id}. {message}")

    # Before a message reaches to services within, it is evaluated by all traffic processors
    # While they are returning true, everything is ok. Once they return false, the message processing stops
    # Traffic processors are free to send any reply as they see fit
    # TODO: Firewall does not return a response and currently we want it in some instances to return it and in
    #       some instances we don't. This is not a good situation.
    for processor in current_node.traffic_processors:
        # TODO Traffic processor responses are not correctly delayed
        result, delay = await processor.process_message(message)
        processing_time += delay
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
            if message.type == MessageType.RESPONSE:
                return

            # TODO: Parametrization of platform
            processing_time += msecs(20).to_float()
            response = ResponseImpl(message, Status(StatusOrigin.NODE, StatusValue.ERROR),
                                    "Nonexistent service {} at node {}".format(message.dst_service, message.dst_ip),
                                    session=message.session, auth=message.auth)
            self._environment_messaging.send_message(response, processing_time)

        # Service exists and it is passive
        elif ServiceImpl.cast_from(current_node.services[message.dst_service]).passive:
            # Passive services just discard the responses and only process the requests
            if message.type == MessageType.RESPONSE:
                return

            if current_node.services[message.dst_service].passive_service.state != ServiceState.RUNNING:
                response = ResponseImpl(message, Status(StatusOrigin.NODE, StatusValue.ERROR),
                                        "Service {} at node {} is not running".format(message.dst_service, message.dst_ip),
                                        session=message.session, auth=message.auth)
                self._environment_messaging.send_message(response, processing_time)
            else:
                # Delay it by the time it took to process the last hop
                result, processing_time = self._platform_interface.execute_task(message, current_node.services[message.dst_service], current_node, processing_time)
                # delay, response = self._process_passive(message, current_node)
                # processing_time += delay
                # if response.status.origin == StatusOrigin.SYSTEM and response.status.value == StatusValue.ERROR:
                #    print("Could not process the request, unknown semantics.")
                # else:
                #    self._environment_messaging.send_message(response, processing_time)
        # Service exists and it is active
        else:
            # An active service does not necessarily produce Responses, so we should just move time
            # somehow and be done with it.
            # TODO How to move time? (I now know why, I need to investigate why)

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

            # TODO: CAM Ignored for now
            # if self._cam.is_composite(message.id):
            #     self._cam.incoming_message(message)
            # else:
            # result, delay = current_node.services[message.dst_service].active_service.process_message(message)
            result, delay = self._platform_interface.execute_task(message, current_node.services[message.dst_service], current_node, processing_time)

    # If no service is specified, it is a message to a node, but still, it is processed as a request for
    # passive service and processed with the interpreter
    # No service is specified
    else:
        # If there is response arriving without destination service, just drop it
        if message.type == MessageType.RESPONSE:
            return

        # If it is a request, then it is processed as a request for passive service and processed with the interpreter
        # Delay it by the time it took to process the last hop
        result, delay = self._platform_interface.execute_task(message, None, current_node, processing_time)
        # delay, response = self._process_passive(message, current_node) #MYPY: messageimpl vs request
        # processing_time += delay
        # if response.status.origin == StatusOrigin.SYSTEM and response.status.value == StatusValue.ERROR: #MYPY: same as above, response None?
        #    print("Could not process the request, unknown semantics.")
        # else:
        #    self._environment_messaging.send_message(response, processing_time)