from typing import Any, Dict, Optional, Tuple

from cyst.api.environment.message import Message, MessageType, Request, Status, StatusOrigin, StatusValue
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.host.service import ActiveService, ActiveServiceDescription

from cyst.api.utils.log import get_logger


class ForwardShell(ActiveService):

    def __init__(self,
                 msg: EnvironmentMessaging,
                 res: EnvironmentResources,
                 args: Optional[Dict[str, Any]] = None) -> None:
        self._messaging = msg
        self._resources = res
        self._log = get_logger("services.forward_shell")
        self._ignore_requests: bool = args is None or args.get("ignore_requests", True)

    def run(self) -> None:
        self._log.info("Launched a forward shell service")

    def process_message(self, message: Message) -> Tuple[bool, int]:
        self._log.debug(f"Processing message: {message.id} : {str(message)}")

        if message.type is not MessageType.REQUEST:
            return False, 0

        request = message.cast_to(Request)

        if request.action.id == "cyst:active_service:open_session":
            self._log.debug(f"Openning session for {request.src_service}")
            self._respond_with_session(request)
            return True, 1

        if not self._ignore_requests:
            self._respond_with_error(request, f"Invalid action {request.action.id}")

        return False, 1

    def _respond_with_session(self, request: Request) -> None:
        session = self._messaging.open_session(request)
        response = self._messaging.create_response(request,
                                                   Status(StatusOrigin.SERVICE,
                                                          StatusValue.SUCCESS),
                                                   session=session)
        self._messaging.send_message(response)

    def _respond_with_error(self, request: Request, error: str) -> None:
        response = self._messaging.create_response(
            request, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), error)

        self._messaging.send_message(response)


def create_shell(msg: EnvironmentMessaging, res: EnvironmentResources,
                 args: Optional[Dict[str, Any]]) -> ActiveService:
    return ForwardShell(msg, res, args)


service_description = ActiveServiceDescription(
    "forward_shell",
    "A service acting as a forward shell. It will create a session given the correct action",
    create_shell)
