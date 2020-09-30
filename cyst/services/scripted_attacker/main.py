from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any

from cyst.api.logic.action import Action
from cyst.api.logic.access import Authorization, AccessLevel
from cyst.api.environment.environment import EnvironmentMessaging
from cyst.api.environment.message import Request, Response, MessageType, Message
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.network.session import Session
from cyst.api.host.service import ActiveService, ActiveServiceDescription, Service


class ScriptedAttackerControl(ABC):
    @abstractmethod
    def execute_action(self, target: str, service: str, action: Action, session: Session = None, authorization: Authorization = None) -> None:
        pass

    @abstractmethod
    def get_last_response(self) -> Optional[Response]:
        pass


class ScriptedAttacker(ActiveService, ScriptedAttackerControl):
    def __init__(self, env: EnvironmentMessaging = None, res: EnvironmentResources = None, args: Optional[Dict[str, Any]] = None) -> None:
        self._env = env
        self._responses = []

    # This attacker only runs given actions. No own initiative
    def run(self):
        print("Launched a scripted attacker")

    def execute_action(self, target: str, service: str, action: Action, session: Session = None, authorization: Authorization = None) -> None:
        request = self._env.create_request(target, service, action, session=session, authorization=authorization)
        self._env.send_message(request)

    def process_message(self, message: Message) -> Tuple[bool, int]:
        print("Got response on request {} : {}".format(message.id, str(message)))
        self._responses.append(message)
        return True, 1

    def get_last_response(self) -> Optional[Response]:
        if not self._responses:
            return None
        else:
            return self._responses[-1]

    @staticmethod
    def cast_from(o: Service) -> 'ScriptedAttacker':
        if o.active_service:
            # Had to do it step by step to shut up the validator
            service = o.active_service
            if isinstance(service, ScriptedAttacker):
                return service
            else:
                raise ValueError("Malformed underlying object passed with the Session interface")
        else:
            raise ValueError("Not an active service passed")


def create_attacker(msg: EnvironmentMessaging, res: EnvironmentResources, args: Optional[Dict[str, Any]]) -> ActiveService:
    attacker = ScriptedAttacker(msg, res, args)
    return attacker


service_description = ActiveServiceDescription(
    "scripted_attacker",
    "An attacker that only performs given actions. No logic whatsoever.",
    create_attacker
)