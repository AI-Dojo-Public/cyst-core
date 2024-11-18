import logging

from typing import Any, Dict, Optional, Tuple

from netaddr import IPAddress

from cyst.api.environment.message import Message, MessageType, Request, Response, Status, StatusOrigin, StatusValue
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.host.service import ActiveService, ActiveServiceDescription


class ReverseShell(ActiveService):

    def __init__(self,
                 msg: EnvironmentMessaging,
                 res: EnvironmentResources,
                 id: str,
                 args: Optional[Dict[str, Any]] = None) -> None:
        self._messaging = msg
        self._resources = res
        self._id = id
        self._log = logging.getLogger("services.reverse_shell")

        self._success_sent = False
        if args and (origin := args.get("origin")):
            self._origin_request: Request = origin
        else:
            raise ValueError("Reverse shell requires the request which inicialized it")

        self._delay: int = delay if args and (delay := args.get("delay")) else 0
        self._ignore_requests = args is None or args.get("ignore_requests", True)

        if args and (target := args.get("target")):
            self._target: Tuple[IPAddress, str] = target  # (ip, service)
        else:
            raise ValueError("Reverse shell requires target parameter")

        if not (action := res.action_store.get("cyst:active_service:open_session")):
            raise KeyError("Action 'open_session' is not present in action store")
        self._open_session = action

    async def run(self) -> None:
        self._log.info("Launched a reverse shell service")
        self._log.debug(f"Sending intial request to {self._target}")
        self._request_open_session(delay=0)

    async def process_message(self, message: Message) -> Tuple[bool, int]:
        self._log.debug(f"Processing message {message.id} : {message}")

        is_from_target = (message.src_ip, message.src_service) == self._target

        if message.type is MessageType.RESPONSE and is_from_target:
            response = message.cast_to(Response)

            if not self._success_sent:
                if response.status.value is StatusValue.SUCCESS:
                    self._log.debug(f"Sending final response back to {self._origin_request.id}")
                    self._send_success_to_origin()
                else:
                    self._respond_with_error(self._origin_request, "Failed to open session")

            self._log.debug(f"Sending another open session request to {self._target}")
            self._request_open_session(self._delay)
            return True, 1

        if message.type is MessageType.REQUEST and not self._ignore_requests:
            self._respond_with_error(message.cast_to(Request), "Service doesn't accept requests")

        return False, 1

    def _request_open_session(self, delay: int) -> None:
        dst_address, dst_service = self._target
        request = self._messaging.create_request(dst_address, dst_service, self._open_session)
        self._messaging.send_message(request, delay)

    def _respond_with_error(self, request: Request, error: str) -> None:
        response = self._messaging.create_response(
            request, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), error)
        self._messaging.send_message(response)

    def _send_success_to_origin(self) -> None:
        request = self._origin_request
        response = self._messaging.create_response(request,
                                                   Status(StatusOrigin.SERVICE,
                                                          StatusValue.SUCCESS),
                                                   f"Session opened as a reaction to {self._origin_request.id}",
                                                   session=request.session)
        self._messaging.send_message(response)
        self._success_sent = True


def create_shell(msg: EnvironmentMessaging, res: EnvironmentResources,
                 id:str, args: Optional[Dict[str, Any]]) -> ActiveService:
    return ReverseShell(msg, res, id, args)


service_description = ActiveServiceDescription(
    "reverse_shell",
    "A service acting as a reverse shell. It will send an 'open_session' action to the given endpoint",
    create_shell)
