from __future__ import annotations

import sys

from heapq import heappush
from netaddr import IPAddress
from typing import TYPE_CHECKING, Optional, Any, Union, Dict, List

from cyst.api.environment.message import Request, Response, Status, Message, MessageType
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.logic.access import Authorization, AuthenticationTarget, AuthenticationToken
from cyst.api.logic.action import Action, ActionType
from cyst.api.logic.metadata import Metadata
from cyst.api.network.session import Session
from cyst.api.host.service import ActiveService
from cyst.api.utils.counter import Counter

if TYPE_CHECKING:
    from cyst.core.environment.environment import _Environment


class EnvironmentMessagingImpl(EnvironmentMessaging):
    def __init__(self, env: _Environment):
        self._env = env

    def send_message(self, message: Message, delay: int = 0) -> None:
        _send_message(self._env, message, delay)

    def create_request(self, dst_ip: Union[str, IPAddress], dst_service: str = "", action: Optional[Action] = None,
                       session: Optional[Session] = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None,
                       original_request: Optional[Request] = None) -> Request:
        return self._env.platform.messaging.create_request(dst_ip, dst_service, action, session, auth, original_request)

    def create_response(self, request: Request, status: Status, content: Optional[Any] = None,
                        session: Optional[Session] = None,
                        auth: Optional[Union[Authorization, AuthenticationTarget]] = None,
                        original_response: Optional[Response] = None):
        return self._env.platform.messaging.create_response(request, status, content, session, auth, original_response)

    def open_session(self, request: Request) -> Session:
        return self._env.platform.messaging.open_session(request)


# ----------------------------------------------------------------------------------------------------------------------
def extract_metadata_action(action: Action, action_list: List[Action]):
    if not action.components:
        action_list.append(action)
    else:
        for c in action.components:
            extract_metadata_action(c, action_list)


def _send_message(self: _Environment, message: Message, delay: int = 0) -> None:
    # Get caller service id
    # HACK: This is patently ugly, but oh so much better from the API point of view. So, future me, do not think bad of your past self...
    if isinstance(message, Request):
        caller = sys._getframe(2).f_locals["self"]
        if isinstance(caller, ActiveService):
            message.platform_specific["caller_id"] = self._service_store.get_active_service_id(id(caller))

    # ------------------------------------------------------------------------------------------------------------------
    # Message sending pre-processing
    # ------------------------------------------------------------------------------------------------------------------
    # I would much rather check by the MessageType, but then the type inspection would not work down the line :-/
    if isinstance(message, Request) or isinstance(message, Response):

        # --------------------------------------------------------------------------------------------------------------
        # Message components extraction
        # --------------------------------------------------------------------------------------------------------------
        # Call the behavioral model to add components to direct actions
        message.action.components.extend(self._behavioral_models[message.action.namespace].action_components(message))


    # Send it to the platform.
    # Composite actions are another can of worms. TODO
    self._platform.messaging.send_message(message, delay)

    if message.type is MessageType.REQUEST and message.platform_specific["caller_id"] in self._pause_on_request:
        self._pause = True

    """
    action_type = None
    if isinstance(message, Request) or isinstance(message, Response):
        action_type = ActionImpl.cast_from(message.action).type

    # ------------------------------------------------------------------------------------------------------------------
    # Message sending pre-processing
    # ------------------------------------------------------------------------------------------------------------------
    # Unlike timeouts, request and responses have more processing associated with action compositing, components and
    # metadata association.
    if message.type == MessageType.REQUEST or message.type == MessageType.RESPONSE:
        # --------------------------------------------------------------------------------------------------------------
        # Composite action handling
        # --------------------------------------------------------------------------------------------------------------
        # Composite actions "happen" only at the point of sending, i.e., actual messages with actions that have any
        # observable effect are the constituent ones. Therefore, they are not subject to typical send_message processing.
        if action_type == ActionType.COMPOSITE:
            if message.type == MessageType.REQUEST:
                # Composite action manager will send all constituent messages and will prepare the response that will
                # be sent by normal channels.

                # We have to double the code to get the source IP, which is unfortunate, but I am not sure, how to
                # compress the logic and still keep it readable
                if message.session:
                    message.set_src_ip(message.path[0].src.ip)
                else:
                    source = self._network.get_node_by_id(message.origin.id)
                    gateway, port = source.gateway(message.dst_ip)
                    if not gateway:
                        raise Exception("Could not send a message, no gateway to route it through.")

                    iface = InterfaceImpl.cast_from(source.interfaces[port])
                    message.set_src_ip(iface.ip)

                    message.set_origin(Endpoint(source.id, port, iface.ip))

                # TODO: What to do about delay?
                self._cam.execute_request(message, delay)
            else:
                if self._cam.is_top_level(message.id):
                    source = self._network.get_node_by_id(message.origin.id)
                    source.services[message.dst_service].active_service.process_message(message)
                else:
                    self._cam.incoming_message(message)
            return

        # --------------------------------------------------------------------------------------------------------------
        # Message components extraction
        # --------------------------------------------------------------------------------------------------------------
        # Call the behavioral model to add components to direct actions
        message.action.components.extend(self._behavioral_models[message.action.namespace].action_components(message))

        # --------------------------------------------------------------------------------------------------------------
        # Metadata enrichment
        # --------------------------------------------------------------------------------------------------------------
        # Enrich the message with metadata. The rule of thumb is that actions with components get the metadata from
        # them. Otherwise, their metadata provider is queried.
        action_queue = []
        extract_metadata_action(message.action, action_queue)

        message_metadata = Metadata()
        message_metadata.flows = []

        # TODO: This is only temporary and probably a subject to changes, because of many undefined corner cases
        for action in action_queue:
            for namespace, provider in self._metadata_providers.items():
                if action.id.startswith(namespace):
                    metadata = provider.get_metadata(action, message)
                    # TODO: Currently we are only considering flows
                    if metadata.flows:
                        message_metadata.flows.extend(metadata.flows)

        message.set_metadata(message_metadata)

    # ------------------------------------------------------------------------------------------------------------------
    # Actual message sending
    # ------------------------------------------------------------------------------------------------------------------
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

    message.sent = True

    self._message_log.debug(f"[time: {self._time}] Sending a message: {str(message)}")

    if message.type is MessageType.REQUEST and f"{message.origin.id}.{message.src_service}" in self._pause_on_request:
        self._pause = True
    """