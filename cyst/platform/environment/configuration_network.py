from __future__ import annotations

from typing import TYPE_CHECKING, List, Union, Optional

from cyst.api.environment.configuration import NetworkConfiguration
from cyst.api.environment.message import Message, MessageType
from cyst.api.network.elements import Connection
from cyst.api.network.node import Node
from cyst.api.network.session import Session

from cyst.platform.environment.message import MessageImpl
from cyst.platform.host.service import ServiceImpl
from cyst.platform.network.elements import PortImpl
from cyst.platform.network.session import SessionImpl
from cyst.platform.network.node import NodeImpl

if TYPE_CHECKING:
    from cyst.platform.main import CYSTPlatform


class NetworkConfigurationImpl(NetworkConfiguration):
    def __init__(self, platform: CYSTPlatform):
        self._platform = platform

    def add_node(self, node: Node) -> None:
        return _add_node(self._platform, node)

    def add_connection(self, source: Node, target: Node, source_port_index: int = -1, target_port_index: int = -1,
                       net: str = "", connection: Optional[Connection] = None) -> Connection:
        return _add_connection(self._platform, source, target, source_port_index, target_port_index, net, connection)

    def get_connections(self, node: Node, port_index: Optional[int] = None) -> List[Connection]:
        return [ifc.connection for ifc in node.interfaces if ifc.connection and
                (not port_index or PortImpl.cast_from(ifc)._index == port_index)]

    def create_session(self, owner: str, waypoints: List[Union[str, Node]], src_service: Optional[str] = None,
                       dst_service: Optional[str] = None, parent: Optional[Session] = None,
                       defer: bool = False, reverse: bool = False, id: Optional[str] = None) -> Optional[Session]:
        return _create_session(self._platform, owner, waypoints, src_service, dst_service, parent, defer, reverse, id)

    def create_session_from_message(self, message: Message, reverse_direction: bool = False) -> Session:
        return _create_session_from_message(self._platform, message, reverse_direction)

    def append_session(self, original_session: Session, appended_session: Session) -> Session:
        return _append_session(self._platform, original_session, appended_session)


# ------------------------------------------------------------------------------------------------------------------
# NetworkConfiguration
def _add_node(self: CYSTPlatform, node: Node) -> None:
    self._network.add_node(NodeImpl.cast_from(node))


def _add_connection(self: CYSTPlatform, source: Node, target: Node, source_port_index: int = -1, target_port_index: int = -1,
                   net: str = "", connection: Connection = None) -> Connection:
    return self._network.add_connection(NodeImpl.cast_from(source), source_port_index, NodeImpl.cast_from(target),
                                        target_port_index, net, connection)


# TODO: Decide if we want to have service association a part of the session creation, or if we rather leave it
#       to service interface
def _create_session(self: CYSTPlatform, owner: str, waypoints: List[Union[str, Node]], src_service: Optional[str] = None,
                    dst_service: Optional[str] = None, parent: Optional[Session] = None, defer: bool = False,
                    reverse: bool = False, id: Optional[str] = None) -> Optional[Session]:

    if defer:
        self._sessions_to_add.append((owner, waypoints, src_service, dst_service, parent, reverse, id))
        return None
    else:
        session = self._network.create_session(owner, waypoints, src_service, dst_service, parent, reverse, id)
        if src_service or dst_service:
            if not src_service and dst_service:
                raise RuntimeError("Both or neither services must be specified during session creation.")

            src_node: Node
            if isinstance(waypoints[0], str):
                src_node = self._network.get_node_by_id(waypoints[0])
            else:
                src_node = waypoints[0]

            dst_node: Node
            if isinstance(waypoints[-1], str):
                dst_node = self._network.get_node_by_id(waypoints[-1])
            else:
                dst_node = waypoints[-1]

            ServiceImpl.cast_from(src_node.services[src_service]).add_session(session)
            ServiceImpl.cast_from(dst_node.services[dst_service]).add_session(session)
        return session


def _append_session(self: CYSTPlatform, original_session: Session, appended_session: Session) -> Session:
    original = SessionImpl.cast_from(original_session)
    appended = SessionImpl.cast_from(appended_session)

    src_service = original._src_service
    dst_service = appended._dst_service

    node = self._network.get_node_by_id(original.startpoint.id)
    session = SessionImpl(original.owner, original, appended.path_id, src_service, dst_service)

    ServiceImpl.cast_from(node.services[src_service]).add_session(session)

    return session


def _create_session_from_message(self: CYSTPlatform, message: Message, reverse_direction: bool = False) -> Session:
    message = MessageImpl.cast_from(message)

    if message.auth:
        owner = message.auth.identity
    else:
        owner = message.dst_service
    path = message.non_session_path
    parent = message.session

    # In case someone attempts to create another session in the endpoint of already provided session, just return
    # that session instead.
    # TODO: Document this behavior
    if not path:
        return parent

    # Source and destination services are taken from message and the session reference is inserted to both
    if message.type == MessageType.REQUEST:
        src_service = message.src_service
        dst_service = message.dst_service
    else:
        src_service = message.dst_service
        dst_service = message.src_service

    if reverse_direction:
        path = [hop.swap() for hop in reversed(path)]
        src_service, dst_service = dst_service, src_service

    session = SessionImpl(owner, parent, path, src_service, dst_service, self._network)

    if parent:
        p = SessionImpl.cast_from(parent)
        src_node = self._network.get_node_by_id(p.startpoint.id)
    else:
        src_node = self._network.get_node_by_id(path[0].src.id)
    dst_node = self._network.get_node_by_id(path[-1].dst.id)

    ServiceImpl.cast_from(src_node.services[src_service]).add_session(session)
    ServiceImpl.cast_from(dst_node.services[dst_service]).add_session(session)

    return session
