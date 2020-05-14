from enum import Enum
from typing import Any, List, Optional, Union
from netaddr import *

from environment.action import Action
from environment.access import Authorization
from environment.network_elements import Endpoint, Hop
from utils.counter import Counter


class MessageType(Enum):
    TIMEOUT = 0
    REQUEST = 1
    RESPONSE = 2


class _Message:
    def __init__(self, type: MessageType, origin: Endpoint = None, src_ip: IPAddress = None, dst_ip: IPAddress = None,
                 src_service: str = "", dst_service: str = "", session: 'Session' = None,
                 authorization: Authorization = None, force_id: int = -1, ttl: int = 64) -> None:
        # Messages are globally indexed so that they can be ordered and are unique
        if force_id == -1:
            self._id = Counter().get("message")
        else:
            self._id = force_id

        self._type = type
        self._origin = origin
        self._src_ip = src_ip
        self._dst_ip = dst_ip
        self._src_service = src_service
        self._dst_service = dst_service
        self._current = origin
        self._session = session
        self._authorization = authorization

        self._path = []
        self._non_session_path = []

        self._sent = False
        self._next_hop = None

        self._session_iterator = None
        self._in_session = False

        self._ttl = ttl

    @property
    def id(self) -> int:
        return self._id

    @property
    def type(self) -> MessageType:
        return self._type

    @property
    def origin(self) -> Optional[Endpoint]:
        return self._origin

    def set_origin(self, value: Endpoint) -> None:
        self._origin = value
        # Setting origin automatically resets the value of current endpoint
        self._current = value

    @property
    def src_ip(self) -> Optional[IPAddress]:
        return self._src_ip

    def set_src_ip(self, value: IPAddress) -> None:
        self._src_ip = value

    @property
    def dst_ip(self) -> Optional[IPAddress]:
        return self._dst_ip

    @property
    def sent(self) -> bool:
        return self._sent

    @property
    def current(self) -> Optional[Endpoint]:
        return self._current

    @sent.setter
    def sent(self, value) -> None:
        self._sent = True

    @property
    def in_session(self) -> bool:
        return self._in_session

    def hop(self) -> None:
        self._current = self._next_hop

    @property
    def next_hop(self) -> Optional[Endpoint]:
        return self._next_hop

    # Next hop can be explicitly set by a switch, or can be taken from an active session
    def set_next_hop(self, origin_endpoint: Endpoint = None, destination_endpoint: Endpoint = None) -> None:
        if origin_endpoint and destination_endpoint:
            self._non_session_path.append(Hop(origin_endpoint, destination_endpoint))
            self._path.append(Hop(origin_endpoint, destination_endpoint))
            self._next_hop = destination_endpoint
        else:
            # If it does not have a session then something is very wrong
            if not self._session:
                raise Exception("Message does not have a session to get next hop from")

            # Get a session iterator if the message did not enter session yet
            if not self._session_iterator:
                if self.type == MessageType.REQUEST:
                    self._session_iterator = self._session.get_forward_iterator()
                elif self.type == MessageType.RESPONSE:
                    self._session_iterator = self._session.get_reverse_iterator()
                else:
                    raise Exception("Attempting to send message other than request/response through session")

                self._in_session = True

            hop = next(self._session_iterator)
            src = hop.src
            self._next_hop = hop.dst

            if self._current.port == -1:
                self.set_origin(src)

            self._path.append(Hop(src, self._next_hop))

            # If the next hop is one of the session's end, turn off session flag
            if (self.type == MessageType.REQUEST and self._next_hop.id == self._session.endpoint.id) or \
                    (self.type == MessageType.RESPONSE and self._next_hop.id == self._session.start.id):
                self._in_session = False

    # Can't really type it other then using string literal, because of dependency issues
    @property
    def session(self) -> 'Session':
        return self._session

    @session.setter
    def session(self, value: 'Session') -> None:
        self._session = value

    @property
    def authorization(self) -> Authorization:
        return self._authorization

    @authorization.setter
    def authorization(self, value: Authorization) -> None:
        self._authorization = value

    def __str__(self) -> str:
        result = "Message: [ID: {}, Type: {}, Origin: {}, Source: {}, Target: {}, Session: {}, Authorization: {}]"\
                 .format(self.id, self.type.name, self._origin, self.src_ip, self.dst_ip, self.session, self.authorization)
        return result

    def __lt__(self, other) -> bool:
        if self.type.value != other.type.value:
            return self.type.value < other.type.value
        else:
            return self.id < other.id

    @property
    def path(self) -> List[Hop]:
        return self._path

    @property
    def non_session_path(self) -> List[Hop]:
        return self._non_session_path

    @property
    def src_service(self):
        return self._src_service

    @property
    def dst_service(self):
        return self._dst_service

    @property
    def ttl(self):
        return self._ttl

    def decrease_ttl(self):
        self._ttl -= 1
        return self._ttl


class Request(_Message):
    def __init__(self, dst_ip: Union[str, IPAddress], dst_service: str = "", src_service: str = "", action: Action = None,
                 session: 'Session' = None, authorization: Authorization = None):

        if type(dst_ip) is str:
            dst_ip = IPAddress(dst_ip)

        super(Request, self).__init__(MessageType.REQUEST, None, None, dst_ip, src_service, dst_service,
                                      session=session, authorization=authorization)

        self._action = action

    @property
    def action(self) -> Action:
        return self._action

    @property
    def src_service(self) -> str:
        return self._src_service

    @property
    def dst_service(self) -> str:
        return self._dst_service

    def __str__(self) -> str:
        result = "Request: [ID: {}, Type: {}, Origin: {}, Source: {}, Target: {}, Destination service: {}, Source service: {}, Actions: {}, Session: {}, Authorization: {}]"\
                   .format(self.id, self.type.name, self._origin, self.src_ip, self.dst_ip, self.dst_service, self.src_service, [x.name for x in self.action.tags],
                           self.session, self.authorization)
        return result


# TODO No repeated encapsulation of content yet
class Content:
    def __init__(self, encrypted_for=None, tokens=None, data=None):
        self._encrypted_for = encrypted_for
        self._tokens = tokens
        self._data = data


class StatusOrigin(Enum):
    NETWORK = 0
    NODE = 1
    SERVICE = 2
    SYSTEM = 99


class StatusValue(Enum):
    SUCCESS = 0
    FAILURE = 1
    ERROR = 2


class Status:
    def __init__(self, origin=None, value=None):
        self._origin = origin
        self._value = value

    def __str__(self) -> str:
        return "({}, {})".format(self._origin.name, self._value.name)

    def __eq__(self, other: 'Status') -> bool:
        return self._origin == other._origin and self._value == other._value

    @property
    def origin(self) -> StatusOrigin:
        return self._origin

    @property
    def value(self) -> StatusValue:
        return self._value


class Response(_Message):
    def __init__(self, request: _Message, status: Status = None,
                 content: Any = None, session: 'Session' = None, authorization: Authorization = None) -> None:
        super(Response, self).__init__(MessageType.RESPONSE, request.current, request.dst_ip, request.src_ip, session=session, authorization=authorization, force_id=request.id)
        self._status = status
        self._content = content
        # Response switches the source and destination services
        self._src_service = request.dst_service
        self._dst_service = request.src_service
        self._non_session_path = request._non_session_path
        self._path_index = len(self._non_session_path)
        self.set_origin(request.current)

    def set_next_hop(self, origin_endpoint: Endpoint = None, destination_endpoint: Endpoint = None) -> None:
        # Traversing the pre-session connections is done by traversing back the non-session path
        # The rest is up to session management of message
        if self._path_index == 0 or self._in_session:
            return super(Response, self).set_next_hop()

        self._path_index -= 1
        self._next_hop = self._non_session_path[self._path_index].src

    def __str__(self) -> str:
        result = "Response: [ID: {}, Type: {}, Origin: {}, Source: {}, Target: {}, Status: {}, Content: {}, Session: {}, Authorization: {}]"\
                   .format(self.id, self.type.name, self._origin, self.src_ip, self.dst_ip, self._status, self._content, self.session, self.authorization)
        return result

    @property
    def status(self):
        return self._status

    @property
    def content(self):
        return self._content

    def set_in_session(self, value: bool = False) -> None:
        self._in_session = value
