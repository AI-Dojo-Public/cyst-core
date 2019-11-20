from enum import Enum
from typing import Any, List

from environment.action import Action
from environment.access import Authorization


class MessageType(Enum):
    TIMEOUT = 0
    REQUEST = 1
    RESPONSE = 2
    ACK = 3


class Message:
    def __init__(self, id: str, type: MessageType, source: str, target: str, session: 'Session' = None,
                 authorization: Authorization = None):
        self._id = id
        self._type = type
        self._source = source
        self._target = target
        self._current = source
        self._path = []
        self._non_session_path = []
        # This is probably not a very clean solution, but there is up to two node difference between the effect
        # of self._in_session and hop function
        self._write_non_session = True
        self._sent = False
        self._next_hop = None
        self._session = session
        self._session_iterator = None
        self._in_session = False
        self._authorization = authorization

    @property
    def id(self):
        return self._id

    @property
    def type(self):
        return self._type

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

    @property
    def sent(self):
        return self._sent

    @property
    def current(self):
        return self._current

    @sent.setter
    def sent(self, value):
        self._sent = True

    @property
    def in_session(self) -> bool:
        return self._in_session

    def hop(self):
        if self._session and self.current == self._session.endpoint:
            self._write_non_session = True

        if self._write_non_session:
            self._non_session_path.append(self._current)

        self._path.append(self._current)
        self._current = self._next_hop

    @property
    def next_hop(self) -> str:
        return self._next_hop

    # Next hop can be explicitly set by a switch, or can be taken from an active session
    def set_next_hop(self, node: str = "") -> None:
        if not node:
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
                self._write_non_session = False

            # Move it to another hop
            self._next_hop = next(self._session_iterator)
            # Sessions contain both their origins and destinations. So session chain will have duplicates on
            # session borders
            if self._next_hop == self._current:
                self._next_hop = next(self._session_iterator)

            # If the next hop is the session end, turn off session flag
            if self._next_hop == self._session.endpoint:
                self._in_session = False
        else:
            self._next_hop = node

    # Can't really type it other then using string literal, because of dependency issues
    @property
    def session(self) -> 'Session':
        return self._session

    def set_session(self, session: 'Session') -> None:
        self._session = session

    @property
    def authorization(self) -> Authorization:
        return self._authorization

    def set_authorization(self, authorization: Authorization) -> None:
        self._authorization = authorization

    def __str__(self):
        result = "Message: [ID: {}, Type: {}, Source: {}, Target: {}, Session: {}, Authorization: {}]"\
                 .format(self.id, self.type.name, self.source, self.target, self.session, self.authorization)
        return result

    def __lt__(self, other) -> bool:
        return self.id < other.id

    @property
    def path(self) -> List[str]:
        return self._path

    @property
    def non_session_path(self) -> List[str]:
        return self._non_session_path


class Ack(Message):
    def __init__(self, id):
        super(Ack, self).__init__(id, MessageType.ACK, None, None)


class Request(Message):
    def __init__(self, id, source: str = "", target: str = "", service: str = "", action: Action = None,
                 session: 'Session' = None, authorization: Authorization = None):
        super(Request, self).__init__(id, MessageType.REQUEST, source, target, session=session, authorization=authorization)

        self._service = service
        self._action = action

    @property
    def action(self) -> Action:
        return self._action

    @property
    def service(self) -> str:
        return self._service

    def __str__(self) -> str:
        result = "Request: [ID: {}, Type: {}, Source: {}, Target: {}, Service: {}, Actions: {}, Session: {}, Authorization: {}]"\
                   .format(self.id, self.type.name, self.source, self.target, self.service, [x.name for x in self.action.tags],
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


class StatusValue(Enum):
    SUCCESS = 0
    FAILURE = 1
    ERROR = 2


class Status:
    def __init__(self, origin=None, value=None):
        self._origin = origin
        self._value = value

    def __str__(self):
        return "({}, {})".format(self._origin.name, self._value.name)

    @property
    def origin(self):
        return self._origin

    @property
    def value(self):
        return self._value


class Response(Message):
    def __init__(self, id, source: str = None, target: str = None, service: str = None, status: Status = None,
                 content: Any = None, session: 'Session' = None, authorization: Authorization = None) -> None:
        super(Response, self).__init__(id, MessageType.RESPONSE, source, target, session=session, authorization=authorization)
        self._status = status
        self._content = content
        self._service = service

    def __str__(self) -> str:
        result = "Response: [ID: {}, Type: {}, Source: {}, Target: {}, Status: {}, Content: {}, Session: {}, Authorization: {}]"\
                   .format(self.id, self.type.name, self.source, self.target, self._status, self._content, self.session, self.authorization)
        return result

    @property
    def status(self):
        return self._status

    @property
    def content(self):
        return self._content

    @property
    def service(self):
        return self._service
