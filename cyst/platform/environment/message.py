from copy import deepcopy
from typing import Any, List, Optional, Union, Type, Dict, Callable, Tuple
from netaddr import *

from cyst.api.environment.message import MessageType, Message, Request, Response, Status, Timeout, T, Resource, Signal, ComponentState
from cyst.api.host.service import ActiveService
from cyst.api.logic.access import Authorization, AuthenticationToken, AuthenticationTarget
from cyst.api.logic.action import Action
from cyst.api.logic.metadata import Metadata
from cyst.api.network.session import Session
from cyst.api.utils.counter import Counter

from cyst.platform.network.elements import Endpoint, Hop
from cyst.platform.network.session import SessionImpl


# TODO No repeated encapsulation of content yet
class Content:
    def __init__(self, encrypted_for=None, tokens=None, data=None):
        self._encrypted_for = encrypted_for
        self._tokens = tokens
        self._data = data


class MessageImpl(Message):
    def __init__(self, type: MessageType, origin: Endpoint = None, src_ip: IPAddress = None, dst_ip: IPAddress = None,
                 dst_service: str = "", session: Session = None,
                 auth: Optional[Union[Authorization, AuthenticationToken, AuthenticationTarget]] = None, force_id: int = -1, ttl: int = 64) -> None:

        super(MessageImpl, self).__init__()

        # Messages are globally indexed so that they can be ordered and are unique
        if force_id == -1:
            # Timeout is retaining its own counter, because it messes up the IDs if it is used extensively.
            self._id = Counter().get("timeout" if type == MessageType.TIMEOUT else "message")
        else:
            self._id = force_id

        self._type = type
        self._origin = origin
        self._src_ip = src_ip
        self._dst_ip = dst_ip
        self._src_service = ""
        self._dst_service = dst_service
        self._current = origin
        self._session = session
        self._auth = auth

        self._path: List[Hop] = []
        self._non_session_path: List[Hop] = []

        self._sent = False
        self._next_hop = None

        self._session_iterator = None
        self._in_session = False

        self._ttl = ttl

        self._metadata = None
        self._platform_specific: Dict[str, Any] = {}

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

    def set_dst_ip(self, value: IPAddress) -> None:
        self._dst_ip = value

    @property
    def sent(self) -> bool:
        return self._sent

    @sent.setter
    def sent(self, value) -> None:
        self._sent = True

    @property
    def current(self) -> Optional[Endpoint]:
        return self._current


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
            self._next_hop = destination_endpoint #type:ignore #MYPY: Should be fine
        else:
            # If it does not have a session then something is very wrong
            if not self._session:
                raise Exception("Message does not have a session to get next hop from")

            # Get a session iterator if the message did not enter session yet
            if not self._session_iterator:
                if self.type == MessageType.REQUEST:
                    self._session_iterator = SessionImpl.cast_from(self._session).forward_iterator #type:ignore #MYPY: Should be fine
                elif self.type == MessageType.RESPONSE:
                    self._session_iterator = SessionImpl.cast_from(self._session).reverse_iterator #type:ignore #MYPY: Should be fine
                else:
                    raise Exception("Attempting to send message other than request/response through session")

                self._in_session = True

            hop = next(self._session_iterator) #type: ignore #MYPY: probably fine
            src: Endpoint = hop.src
            self._next_hop = hop.dst

            """MYPY: something like this?             if self._current is not None and self._current.port == -1:
                self.set_origin(src)
"""

            if self._current.port == -1:
                self.set_origin(src)

            self._path.append(Hop(src, self._next_hop)) #MYPY: issue with hop, might currently return None, but should not based on annotation

            # If the next hop is one of the session's end, turn off session flag
            if (self.type == MessageType.REQUEST and self._next_hop.id == SessionImpl.cast_from(self._session).endpoint.id) or \
                (self.type == MessageType.RESPONSE and self._next_hop.id == SessionImpl.cast_from(self._session).startpoint.id):
                self._in_session = False #MYPY: if next hop really is None, then the call to id will fail

    # Can't really type it other then using string literal, because of dependency issues
    @property
    def session(self) -> Session:
        return self._session

    @session.setter
    def session(self, value: Session) -> None:
        self._session = value

    @property
    def auth(self) -> Optional[Union[Authorization, AuthenticationToken, AuthenticationTarget]]:
        return self._auth

    @auth.setter
    def auth(self, value: Union[Authorization, AuthenticationToken, AuthenticationTarget]) -> None:
        self._auth = value

    def __str__(self) -> str:
        result = "Message: [ID: {}, Type: {}, Origin: {}, Source: {}, Target: {}, Session: {}, Authorization: {}]"\
                 .format(self.id, self.type.name, self._origin, self.src_ip, self.dst_ip, self.session, self.auth)
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
    def src_service(self) -> str:
        return self._src_service

    @src_service.setter
    def src_service(self, value: str) -> None:
        self._src_service = value

    @property
    def dst_service(self):
        return self._dst_service

    @dst_service.setter
    def dst_service(self, value: str) -> None:
        self._dst_service = value

    @property
    def ttl(self):
        return self._ttl

    def decrease_ttl(self):
        self._ttl -= 1
        return self._ttl

    @property
    def metadata(self) -> Metadata:
        return self._metadata

    def set_metadata(self, metadata: Metadata) -> None:
        self._metadata = metadata

    @property
    def platform_specific(self) -> Dict[str, Any]:
        return self._platform_specific

    @staticmethod
    def cast_from(o: Message) -> 'MessageImpl':
        if isinstance(o, MessageImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Message interface")

    def cast_to(self, type: Type[T]) -> T:
        if isinstance(self, type):
            return self #MYPY: if this works, then probably ignore
        else:
            raise ValueError("Casting to a wrong derived type")


class RequestImpl(MessageImpl, Request):
    def __init__(self, dst_ip: Union[str, IPAddress], dst_service: str = "", action: Action = None,
                 session: Session = None, auth: Optional[Union[Authorization, AuthenticationToken, AuthenticationTarget]] = None,
                 original_request: Optional[Request] = None):

        if type(dst_ip) is str:
            dst_ip = IPAddress(dst_ip)

        _session = session
        if not _session and original_request:
            _session = original_request.session

        _auth = auth
        if not _auth and original_request:
            _auth = original_request.auth

        _origin = None
        if original_request:
            _origin = RequestImpl.cast_from(original_request).origin

        _src_ip = None
        if original_request:
            _src_ip = original_request.src_ip

        super(RequestImpl, self).__init__(MessageType.REQUEST, _origin, _src_ip, dst_ip, dst_service,
                                          session=_session, auth=_auth)

        if original_request:
            self.src_service = original_request.src_service
            self.platform_specific["caller_id"] = original_request.platform_specific["caller_id"]

        self._action = action

    @property
    def action(self) -> Action:
        return self._action

    @action.setter
    def action(self, value):
        self._action = value

    def __str__(self) -> str:
        result = "Request: [ID: {}, Type: {}, Origin: {}, Source: {}, Target: {}, Destination service: {}, Source service: {}, Action: {}, Session: {}, Authorization: {}]"\
                   .format(self.id, self.type.name, self._origin.ip if self.origin else None, self.src_ip, self.dst_ip, self.dst_service, self.src_service, self.action.id,
                           self.session, self.auth)
        return result


        """#MYPY: Maybe something liket this:
            def __str__(self) -> str:
        result = "Request: [ID: {}, Type: {}, Origin: {}, Source: {}, Target: {}, Destination service: {}, Source service: {}, Action: {}, Session: {}, Authorization: {}]"\
                   .format(self.id, self.type.name, self._origin.ip if self._origin is not None else None, self.src_ip, self.dst_ip, self.dst_service, self.src_service, self.action.id if self.action is not None else None,
                           self.session, self.auth)
        return result
        """



    @staticmethod
    def cast_from(o: Request) -> 'RequestImpl':
        if isinstance(o, RequestImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Request interface")


class ResponseImpl(MessageImpl, Response):
    def __init__(self, request: MessageImpl, status: Status = None,
                 content: Any = None, session: Session = None,
                 auth: Optional[Union[Authorization, AuthenticationToken, AuthenticationTarget]] = None,
                 original_response: Optional[Response] = None) -> None:

        super(ResponseImpl, self).__init__(MessageType.RESPONSE, request.current, request.dst_ip, request.src_ip,
                                           session=session, auth=auth, force_id=request.id)

        self._status = status
        self._content = content
        if isinstance(request, Request):
            self._action = request.action
        else:
            raise RuntimeError("Attempting to create a response from non-request Message")
        # Response switches the source and destination services
        self._src_service = request.dst_service
        self._dst_service = request.src_service
        self._non_session_path = request._non_session_path
        self._path_index = len(self._non_session_path)
        self.set_origin(request.current)

        # Copy platform-specific information
        self._platform_specific = request.platform_specific

    def set_next_hop(self, origin_endpoint: Endpoint = None, destination_endpoint: Endpoint = None) -> None:
        # Traversing the pre-session connections is done by traversing back the non-session path
        # The rest is up to session management of message
        if self._path_index == 0 or self._in_session:
            return super(ResponseImpl, self).set_next_hop()

        self._path_index -= 1
        self._next_hop = self._non_session_path[self._path_index].src

    def __str__(self) -> str:
        result = "Response: [ID: {}, Type: {}, Origin: {}, Source: {}, Target: {}, Status: {}, Content: {}, Session: {}, Authorization: {}]"\
                   .format(self.id, self.type.name, self._origin.ip if self._origin else None, self.src_ip, self.dst_ip, self._status, self._content, self.session, self.auth)
        return result

    @property
    def action(self) -> Action:
        return self._action

    @property
    def status(self):
        return self._status

    @property
    def content(self):
        return self._content

    def set_in_session(self, value: bool = False) -> None:
        self._in_session = value

    @staticmethod
    def cast_from(o: Response) -> 'ResponseImpl':
        if isinstance(o, ResponseImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Response interface")

    def __deepcopy__(self, memodict):
        cls = self.__class__
        result = cls.__new__(cls)
        memodict[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "_content":
                setattr(result, "_content", str(v))
            else:
                setattr(result, k, deepcopy(v, memodict))
        return result

class TimeoutImpl(MessageImpl, Timeout):

    def __init__(self, callback: Union[ActiveService, Callable[[Message], Tuple[bool, int]]], start_time: float, duration: float, parameter: Optional[Any]):
        super(TimeoutImpl, self).__init__(MessageType.TIMEOUT)

        self._start_time = start_time
        self._duration = duration
        self._parameter = parameter
        self._callback = callback

    @property
    def start_time(self) -> float:
        return self._start_time

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def parameter(self) -> Any:
        return self._parameter

    @property
    def callback(self) -> Callable[[Message], Tuple[bool, int]]:
        if isinstance(self._callback, ActiveService):
            return self._callback.process_message
        else:
            return self._callback


    def __str__(self) -> str:
        return "Timeout: [Start: {}, Duration: {}, Parameter: {}]".format(self._start_time, self._duration, self._parameter)

    @staticmethod
    def cast_from(o: Timeout) -> 'TimeoutImpl':
        if isinstance(o, TimeoutImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the Request interface")


class ResourceMessageImpl(MessageImpl, Resource):

    def __init__(self, path: str, status: Status, service: str, data: Optional[str]):
        super(ResourceMessageImpl, self).__init__(type=MessageType.RESOURCE, dst_service=service)

        self._path = path
        self._status = status
        self._data = data

    @property
    def path(self) -> str:
        return self._path

    @property
    def status(self) -> Status:
        return self._status

    @property
    def data(self) -> Optional[str]:
        return self._data


class SignalImpl(Signal):
    def __init__(self, signal_origin: str, state: ComponentState, effect_origin: str, effect_message: Optional[int],
                 effect_description: str, effect_parameters: Optional[Dict[str, Any]]):
        self._signal_origin = signal_origin
        self._state = state
        self._effect_origin = effect_origin
        self._effect_message = effect_message if effect_message else -1
        self._effect_description = effect_description
        self._effect_parameters = effect_parameters if effect_parameters else {}
        self._id = Counter().get("message")
        self._local_ip = IPAddress("127.0.0.1")
        self._metadata = Metadata()

    @property
    def signal_origin(self) -> str:
        return self._signal_origin

    @property
    def state(self) -> ComponentState:
        return self._state

    @property
    def effect_origin(self) -> str:
        return self._effect_origin

    @property
    def effect_message(self) -> Optional[int]:
        return self._effect_message

    @property
    def effect_description(self) -> str:
        return self._effect_description

    @property
    def effect_parameters(self) -> Dict[str, Any]:
        return self._effect_parameters

    @property
    def id(self) -> int:
        return self._id

    @property
    def type(self) -> MessageType:
        return MessageType.SIGNAL

    @property
    def src_ip(self) -> Optional[IPAddress]:
        return self._local_ip

    @property
    def dst_ip(self) -> Optional[IPAddress]:
        return self._local_ip

    @property
    def src_service(self) -> Optional[str]:
        return ""

    @property
    def dst_service(self) -> str:
        return ""

    @property
    def session(self) -> Optional[Session]:
        return None

    @property
    def auth(self) -> Optional[Union[Authorization, AuthenticationToken, AuthenticationTarget]]:
        return None

    @property
    def ttl(self) -> int:
        return 0

    @property
    def metadata(self) -> Metadata:
        return self._metadata

    def set_metadata(self, metadata: Metadata) -> None:
        return

    @property
    def platform_specific(self) -> Dict[str, Any]:
        return {}

    def cast_to(self, type: Type[T]) -> T:
        raise ValueError("Cannot cast a signal to a message of a different type")
