from __future__ import annotations

import asyncio
import inspect
import sys

from heapq import heappush
from netaddr import IPAddress
from typing import TYPE_CHECKING, Optional, Any, Union, Dict, List

from cyst.api.environment.data_model import ActionModel
from cyst.api.environment.message import Request, Response, Status, Message, MessageType, StatusValue, StatusOrigin
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.logic.access import Authorization, AuthenticationTarget, AuthenticationToken
from cyst.api.logic.action import Action, ActionType
from cyst.api.logic.metadata import Metadata
from cyst.api.network.node import Node
from cyst.api.network.session import Session
from cyst.api.host.service import ActiveService
from cyst.api.utils.counter import Counter

from cyst.core.logic.action import ActionImpl

if TYPE_CHECKING:
    from cyst.core.environment.environment import _Environment


class EnvironmentMessagingImpl(EnvironmentMessaging):
    def __init__(self, env: _Environment):
        self._env = env

    def send_message(self, message: Message, delay: int = 0) -> None:
        _send_message(self._env, message, delay)

    def create_request(self, dst_ip: Union[str, IPAddress], dst_service: str = "", action: Optional[Action] = None,
                       session: Optional[Session] = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None,
                       original_request: Optional[Request] = None) -> Request:
        return self._env.platform.messaging.create_request(dst_ip, dst_service, action, session, auth, original_request)

    def create_response(self, request: Request, status: Status, content: Optional[Any] = None,
                        session: Optional[Session] = None,
                        auth: Optional[Union[Authorization, AuthenticationTarget]] = None,
                        original_response: Optional[Response] = None):
        return self._env.platform.messaging.create_response(request, status, content, session, auth, original_response)

    def open_session(self, request: Request, reverse_direction: bool = False) -> Session:
        return self._env.platform.messaging.open_session(request, reverse_direction)


# ----------------------------------------------------------------------------------------------------------------------
def extract_metadata_action(action: Action, action_list: List[Action]):
    if not action.components:
        action_list.append(action)
    else:
        for c in action.components:
            extract_metadata_action(c, action_list)


def _send_message(self: _Environment, message: Message, delay: int = 0) -> None:

    if isinstance(message, Request):
        # This is a hack that enables getting the caller of the send_message() function.
        # It is ugly, but better than alternatives.

        # Caller frame is up two places
        caller_frame = inspect.currentframe().f_back.f_back
        caller = caller_frame.f_locals["self"]

        if caller and isinstance(caller, ActiveService):
            caller_id = self._service_store.get_active_service_id(id(caller))
            message.platform_specific["caller_id"] = caller_id
            if not caller_id in self._action_counts:
                self._action_counts[caller_id] = 0

    # I would much rather check by the MessageType, but then the type inspection would not work down the line :-/
    if isinstance(message, Request) or isinstance(message, Response):

        # ------------------------------------------------------------------------------------------------------------------
        # Processing depends on action type
        # ------------------------------------------------------------------------------------------------------------------
        action_type = ActionImpl.cast_from(message.action).type

        # ------------------------------------------------------------------------------------------------------------------
        # Composite actions
        if action_type == ActionType.COMPOSITE:
            # Request are sent to composite action manager to process
            # Responses are processed outside the messaging interface and within the main loop
            if message.type == MessageType.REQUEST:
                self._cam.execute_request(message, delay)
                # Top-level composite actions counts towards the action limit
                caller_id = message.platform_specific["caller_id"]
                action_count = self._action_counts[caller_id] + 1
                self._action_counts[caller_id] = action_count

                if action_count > self._highest_action_count:
                    self._highest_action_count = action_count
                    self._highest_action_actor = caller_id

                action_record = ActionModel.from_request(self.infrastructure.statistics.run_id, message)
                # Composite messages do not have an assigned IP, because they are (in theory) executed locally. So, we
                # select one "random" IP from nodes IP list and use it as a source IP.
                node_id, _ = caller_id.split(".")
                node: Node = self._general_configuration.get_object_by_id(node_id, Node)
                if node.ips:
                    action_record.src_ip = str(node.ips[0])
                self._active_actions[message.id] = action_record
            else:
                # Send it to the platform.
                self._platform.messaging.send_message(message, delay)

        # ------------------------------------------------------------------------------------------------------------------
        # Direct actions
        elif action_type == ActionType.DIRECT:
            # Only non-composite-related messages count towards the action limit
            if message.type == MessageType.REQUEST and not self._cam.is_composite(message.id):
                caller_id = message.platform_specific["caller_id"]
                action_count = self._action_counts[caller_id] + 1
                self._action_counts[caller_id] = action_count

                if action_count > self._highest_action_count:
                    self._highest_action_count = action_count
                    self._highest_action_actor = caller_id

                self._active_actions[message.id] = ActionModel.from_request(self.infrastructure.statistics.run_id,
                                                                            message)

            # --------------------------------------------------------------------------------------------------------------
            # Call the behavioral model to add components to direct actions
            # We ignore actions without behavioral models, such as direct agent-agent actions.
            if message.action.namespace in self._behavioral_models:
                message.action.components.extend(self._behavioral_models[message.action.namespace].action_components(message))

            # --------------------------------------------------------------------------------------------------------------
            # Enrich the message with metadata. The rule of thumb is that actions with components get the metadata from
            # them. Otherwise, their metadata provider is queried.
            action_queue = []
            extract_metadata_action(message.action, action_queue)

            message_metadata = Metadata()
            message_metadata.flows = []

            # TODO: This is only temporary and probably a subject to changes, because of many undefined corner cases
            for action in action_queue:
                for namespace, provider in self._metadata_providers.items():
                    if action.id.startswith(namespace):
                        metadata = provider.get_metadata(action, message)
                        # TODO: Currently we are only considering flows
                        if metadata.flows:
                            message_metadata.flows.extend(metadata.flows)

            message.set_metadata(message_metadata)

            # --------------------------------------------------------------------------------------------------------------
            # Send it to the platform.
            self._platform.messaging.send_message(message, delay)

        # ------------------------------------------------------------------------------------------------------------------
        # Component actions
        # Component actions should never travel through the systems as top-level actions of a message
        else:
            if message.type == MessageType.RESPONSE:
                raise RuntimeError("Component action ended in a response. This indicates error in logic somewhere in the pipeline before.")
            else:
                r = self.messaging.create_response(message.cast_to(Request), status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR),
                                                   content="Component action in response. This should not happen.",
                                                   session=message.session, auth=message.auth)
                self.messaging.send_message(r)
                return

    # Pause on request is called regardless of action type
    if message.type is MessageType.REQUEST and message.platform_specific["caller_id"] in self._pause_on_request:
        self._pause = True
