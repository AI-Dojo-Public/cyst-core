from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any, Union

from cyst.api.logic.action import Action
from cyst.api.logic.access import Authorization, AuthenticationToken
from cyst.api.environment.environment import EnvironmentMessaging
from cyst.api.environment.message import Request, Response, MessageType, Message
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.network.session import Session
from cyst.api.host.service import ActiveService, ActiveServiceDescription, Service
from cyst.api.utils.log import get_logger


class ScriptedActorControl(ABC):
    @abstractmethod
    def execute_action(self, target: str, service: str, action: Action, session: Session = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None) -> None:
        pass

    @abstractmethod
    def get_last_response(self) -> Optional[Response]:
        pass


class ScriptedActor(ActiveService, ScriptedActorControl):
    def __init__(self, env: EnvironmentMessaging = None, res: EnvironmentResources = None, args: Optional[Dict[str, Any]] = None) -> None:
        self._env = env
        self._responses = []
        self._log = get_logger("services.scripted_actor")

    # This Actor only runs given actions. No own initiative
    def run(self):
        self._log.info("Launched a scripted Actor")

    def execute_action(self, target: str, service: str, action: Action, session: Session = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None) -> None:
        request = self._env.create_request(target, service, action, session=session, auth=auth)
        self._env.send_message(request)

    def process_message(self, message: Message) -> Tuple[bool, int]:
        self._log.debug(f"Got response on request {message.id} : {str(message)}")
        self._responses.append(message)
        return True, 1

    def get_last_response(self) -> Optional[Response]:
        if not self._responses:
            return None
        else:
            return self._responses[-1]

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


def create_actor(msg: EnvironmentMessaging, res: EnvironmentResources, args: Optional[Dict[str, Any]]) -> ActiveService:
    actor = ScriptedActor(msg, res, args)
    return actor


service_description = ActiveServiceDescription(
    "scripted_actor",
    "An actor that only performs given actions. No logic whatsoever.",
    create_actor
)