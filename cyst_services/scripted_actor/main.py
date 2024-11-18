import inspect
import logging

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any, Union, Callable, Awaitable

from cyst.api.logic.action import Action
from cyst.api.logic.access import Authorization, AuthenticationToken
from cyst.api.environment.environment import EnvironmentMessaging
from cyst.api.environment.message import Request, Response, MessageType, Message
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.network.session import Session
from cyst.api.host.service import ActiveService, ActiveServiceDescription, Service


class ScriptedActorControl(ABC):
    @abstractmethod
    def execute_action(self, target: str, service: str, action: Action, session: Session = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None) -> None:
        pass

    @abstractmethod
    def get_last_message_type(self) -> Optional[MessageType]:
        pass

    @abstractmethod
    def get_last_request(self) -> Optional[Request]:
        pass

    @abstractmethod
    def get_last_response(self) -> Optional[Response]:
        pass

    @abstractmethod
    def set_run_callback(self, fn: Callable[[EnvironmentMessaging, EnvironmentResources], Awaitable[None]]):
        pass

    @abstractmethod
    def set_request_callback(self, fn: Callable[[EnvironmentMessaging, EnvironmentResources, Message], Tuple[bool, int]]):
        pass

    @abstractmethod
    def set_response_callback(self, fn: Callable[[EnvironmentMessaging, EnvironmentResources, Message], Tuple[bool, int]]):
        pass

    @abstractmethod
    def set_message_callback(self, message_type: MessageType, fn: Callable[[EnvironmentMessaging, EnvironmentResources, Message], Tuple[bool, int]]):
        pass


class ScriptedActor(ActiveService, ScriptedActorControl):
    def __init__(self, env: EnvironmentMessaging = None, res: EnvironmentResources = None, id: str = "", args: Optional[Dict[str, Any]] = None) -> None:
        self._id = id
        self._messaging = env
        self._resources = res
        self._responses = []
        self._requests = []
        self._run_callback = None
        self._response_callback = None
        self._request_callback = None
        self._last_message_type = None
        self._log = logging.getLogger("services.scripted_actor")
        self._callbacks = {}

    # This Actor only runs given actions. No own initiative
    async def run(self):
        self._log.info("Launched a scripted Actor")
        if self._run_callback:
            await self._run_callback(self._messaging, self._resources)

    def execute_action(self, target: str, service: str, action: Action, session: Session = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None) -> None:
        request = self._messaging.create_request(target, service, action, session=session, auth=auth)
        self._messaging.send_message(request)

    async def process_message(self, message: Message) -> Tuple[bool, int]:
        self._last_message_type = message.type

        type_map = {
            MessageType.REQUEST: "request",
            MessageType.RESPONSE: "response",
            MessageType.RESOURCE: "resource"
        }

        message_type = type_map[message.type]

        self._log.debug(f"Got a new {message_type} {message.id} : {str(message)}")

        if message.type == MessageType.REQUEST:
            self._requests.append(message)
        elif message.type == MessageType.RESPONSE:
            self._responses.append(message)

        if message.type in self._callbacks:
            return self._callbacks[message.type](self._messaging, self._resources, message)

        return True, 1

    def get_last_message_type(self) -> Optional[MessageType]:
        return self._last_message_type

    def get_last_request(self, count: int = 1) -> Optional[Union[Request, List[Request]]]:
        if not self._requests:
            return None
        if count == 1:
            return self._requests[-1]
        return self._requests[:-count-1:-1]

    def get_last_response(self, count: int = 1) -> Optional[Union[Response, List[Response]]]:
        if not self._responses:
            return None
        if count == 1:
            return self._responses[-1]
        return self._responses[:-count-1:-1]

    def set_request_callback(self, fn: Callable[[EnvironmentMessaging, EnvironmentResources, Message], Tuple[bool, int]]):
        self._callbacks[MessageType.REQUEST] = fn

    def set_response_callback(self, fn: Callable[[EnvironmentMessaging, EnvironmentResources, Message], Tuple[bool, int]]):
        self._callbacks[MessageType.RESPONSE] = fn

    def set_message_callback(self, message_type: MessageType, fn: Callable[[EnvironmentMessaging, EnvironmentResources, Message], Tuple[bool, int]]):
        self._callbacks[message_type] = fn

    def set_run_callback(self, fn: Callable[[EnvironmentMessaging, EnvironmentResources], Awaitable[Any]]):
        self._run_callback = fn

    @staticmethod
    def cast_from(o: Service) -> 'ScriptedActor':
        if o.active_service:
            # Had to do it step by step to shut up the validator
            service = o.active_service
            if isinstance(service, ScriptedActor):
                return service
            else:
                raise ValueError("Malformed underlying object passed with the Session interface")
        else:
            raise ValueError("Not an active service passed")


def create_actor(msg: EnvironmentMessaging, res: EnvironmentResources, id:str, args: Optional[Dict[str, Any]]) -> ActiveService:
    actor = ScriptedActor(msg, res, id, args)
    return actor


service_description = ActiveServiceDescription(
    "scripted_actor",
    "An actor that only performs given actions. No logic whatsoever.",
    create_actor
)
