from __future__ import annotations

from heapq import heappush
from netaddr import IPAddress
from typing import TYPE_CHECKING, Optional, Any, Union

from cyst.api.environment.message import Request, Response, Status, Message
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.logic.access import Authorization, AuthenticationTarget, AuthenticationToken
from cyst.api.logic.action import Action
from cyst.api.logic.metadata import Metadata
from cyst.api.network.session import Session

from cyst.core.environment.message import RequestImpl, ResponseImpl, MessageImpl, MessageType
from cyst.core.network.elements import Endpoint, InterfaceImpl
from cyst.core.network.session import SessionImpl

if TYPE_CHECKING:
    from cyst.core.environment.environment import _Environment


class EnvironmentMessagingImpl(EnvironmentMessaging):
    def __init__(self, env: _Environment):
        self._env = env

    def send_message(self, message: Message, delay: int = 0) -> None:
        m = MessageImpl.cast_from(message)
        _send_message(self._env, m, delay)

    def create_request(self, dst_ip: Union[str, IPAddress], dst_service: str = "", action: Optional[Action] = None,
                       session: Optional[Session] = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None) -> Request:
        return _create_request(dst_ip, dst_service, action, session, auth)

    def create_response(self, request: Request, status: Status, content: Optional[Any] = None,
                        session: Optional[Session] = None,
                        auth: Optional[Union[Authorization, AuthenticationTarget]] = None):
        return _create_response(request, status, content, session, auth)

    def open_session(self, request: Request) -> Session:
        return _open_session(self._env, request)


# ----------------------------------------------------------------------------------------------------------------------
# Free function implementations of the above class. It is being done this way to shut up the type checking and to
# overcome python's limitation on having a class implemented in multiple files.
def _create_request(dst_ip: Union[str, IPAddress], dst_service: str = "",
                    action: Action = None, session: Session = None,
                    auth: Optional[Union[Authorization, AuthenticationToken]] = None) -> Request:
    request = RequestImpl(dst_ip, dst_service, action, session, auth)
    return request


def _create_response(request: Request, status: Status, content: Optional[Any] = None,
                     session: Optional[Session] = None,
                     auth: Optional[Union[Authorization, AuthenticationTarget]] = None) -> Response:
    # Let's abuse the duck typing and "cast" Request to RequestImpl
    if isinstance(request, RequestImpl):
        response = ResponseImpl(request, status, content, session, auth)
        return response
    else:
        raise ValueError("Malformed request passed to create a response from")


def _open_session(self: _Environment, request: Request) -> Session:
    return self._network_configuration.create_session_from_message(request)


def _send_message(self, message: MessageImpl, delay: int = 0) -> None:
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

    # metadata are appended only for requests ATM. This is to test waters, as there are many different design
    # holes and things which need clarification
    if isinstance(message, Request):
        action = message.action

        if self._metadata_providers and action.namespace in self._metadata_providers:
            provider = self._metadata_providers[action.namespace]
            if provider:
                metadata = provider.get_metadata(action)
            else:
                metadata = Metadata()

            metadata.dst_ip = message.dst_ip
            metadata.dst_service = message.dst_service
            metadata.src_ip = message.src_ip
        else:
            metadata = Metadata()

        message.set_metadata(metadata)

    try:
        heappush(self._tasks, (self._time + delay, message))
    except Exception as e:
        self._message_log.error(f"Error sending a message, reason: {e}")

    message.sent = True

    self._message_log.debug(f"Sending a message: {str(message)}")

    if message.origin.id in self._pause_on_request:
        self._pause = True
