from typing import Tuple, Optional

from environment.action import Action
from environment.access import Authorization
from environment.environment import EnvironmentProxy
from environment.message import Request, Response, MessageType
from environment.network_elements import Session
from environment.node import Node


class SimpleAttacker(Node):
    def __init__(self, id: str, type: str = "Attacker", env: EnvironmentProxy = None) -> None:
        self._env = env
        super(SimpleAttacker, self).__init__(id, type)

        self._responses = []

    # This attacker only runs given actions. No own initiative
    def run(self):
        pass

    def execute_action(self, target: str, service: str, action: Action, session: Session = None, authorization: Authorization = None) -> None:
        request = Request(target, service, action, session=session, authorization=authorization)
        self._env.send_request(request)

    def process_message(self, message) -> Tuple[bool, int]:
        if message.type == MessageType.ACK:
            return True, 0

        print("Got response on request {} : {}".format(message.id, str(message)))

        self._responses.append(message)

        return True, 1

    def get_last_response(self) -> Optional[Response]:
        if not self._responses:
            return None
        else:
            return self._responses[-1]