from typing import Tuple, Optional

from environment.action import Action
from environment.access import Authorization
from environment.environment import EnvironmentProxy
from environment.message import Request, Response, MessageType
from environment.network_elements import Session
from environment.node import ActiveService, AccessLevel


class SimpleAttacker(ActiveService):
    def __init__(self, id: str, owner: str = "nobody", env: EnvironmentProxy = None) -> None:
        super(SimpleAttacker, self).__init__(id, owner, env)
        self._env = env
        self._responses = []
        # This attacker requires root for testing purposes
        self._service_access_level = AccessLevel.ELEVATED

    # This attacker only runs given actions. No own initiative
    def run(self):
        print("Launched a simple attacker with ID: {}".format(self.id))

    def execute_action(self, target: str, service: str, action: Action, session: Session = None, authorization: Authorization = None) -> None:
        request = Request(target, service, self.id, action, session=session, authorization=authorization)
        self._env.send_request(request)

    def process_message(self, message) -> Tuple[bool, int]:

        print("Got response on request {} : {}".format(message.id, str(message)))

        self._responses.append(message)

        return True, 1

    def get_last_response(self) -> Optional[Response]:
        if not self._responses:
            return None
        else:
            return self._responses[-1]
