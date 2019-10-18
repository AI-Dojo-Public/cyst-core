from enum import Enum


class MessageType(Enum):
    TIMEOUT = 0
    REQUEST = 1
    RESPONSE = 2
    ACK = 3


class Message:
    def __init__(self, id, type, source, target):
        self._id = id
        self._type = type
        self._source = source
        self._target = target
        self._current = source
        self._path = []
        self._sent = False
        self._next_hop = None

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

    def hop(self):
        self._path.append(self._current)
        self._current = self._next_hop

    @property
    def next_hop(self) -> str:
        return self._next_hop

    def set_next_hop(self, node: str) -> None:
        self._next_hop = node

    def __str__(self):
        result = "Message: [ID: {}, Type: {}, Source: {}, Target: {}]".format(self.id, self.type.name, self.source, self.target)
        return result


class Ack(Message):
    def __init__(self, id):
        super(Ack, self).__init__(id, MessageType.ACK, None, None)


class Request(Message):
    def __init__(self, id, source=None, target=None, service=None, action=None):
        super(Request, self).__init__(id, MessageType.REQUEST, source, target)

        self._service = service
        self._action = action

    @property
    def action(self):
        return self._action

    @property
    def service(self):
        return self._service

    def __str__(self):
        result = "Request: [ID: {}, Type: {}, Source: {}, Target: {}, Service: {}, Actions: {}]"\
                   .format(self.id, self.type.name, self.source, self.target, self.service, [x.name for x in self.action.tags])
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
    def __init__(self, id, source=None, target=None, service=None, status=None, content=None):
        super(Response, self).__init__(id, MessageType.RESPONSE, source, target)
        self._status = status
        self._content = content
        self._service = service

    def __str__(self):
        result = "Response: [ID: {}, Type: {}, Source: {}, Target: {}, Status: {}, Content: {}]"\
                   .format(self.id, self.type.name, self.source, self.target, self._status, self._content)
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
