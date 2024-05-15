import asyncio
import logging

from typing import Dict, Tuple
from uuid import uuid4

from cyst.api.environment.message import Request, Response, Message, Timeout
from cyst.api.environment.configuration import GeneralConfiguration
from cyst.api.host.service import ActiveService, Service
from cyst.api.logic.behavioral_model import BehavioralModel
from cyst.api.logic.composite_action import CompositeActionManager

from cyst.core.environment.environment import EnvironmentMessagingImpl, EnvironmentResources
from cyst.core.logic.action import ActionImpl, ActionType


class CompositeActionManagerImpl(CompositeActionManager):
    def __init__(self, loop: asyncio.AbstractEventLoop, behavioral_models: Dict[str, BehavioralModel], messaging: EnvironmentMessagingImpl, resources: EnvironmentResources, general: GeneralConfiguration):
        self._loop = loop
        self._futures = {}
        self._incoming_queue = set()
        self._outgoing_queue = set()
        self._composite_queue = set()
        self._coroutines = {}
        self._models = behavioral_models
        self._msg = messaging
        self._res = resources
        self._general = general
        self._processing = False
        self._messages = set()
        self._set_futures = 0
        self._composites_processing = 0
        self._terminate = False
        self._log = logging.getLogger("system")

    def processing(self) -> bool:
        # If we are waiting for something to finish, we are processing
        return bool(self._incoming_queue or self._outgoing_queue or self._composite_queue or self._set_futures > 0)

    def execute_request(self, request: Request, delay: int) -> None:
        self._composite_queue.add(request)
        self._coroutines[request.id] = self._models[request.action.namespace].action_flow(request)

    async def call_action(self, request: Request, delay: float = 0.0) -> None:
        future = self._loop.create_future()
        self._futures[request.id] = future

        if ActionImpl.cast_from(request.action).type == ActionType.COMPOSITE:
            self._composite_queue.add(request)
            self._coroutines[request.id] = self._models[request.action.namespace].action_flow(request)
        else:
            self._outgoing_queue.add(request)

        await future
        self._set_futures -= 1
        return future.result()

    async def delay(self, delay: float = 0.0) -> None:
        future = self._loop.create_future()
        future_id = uuid4()
        self._futures[future_id] = future

        self._res.clock.timeout(self._process_timeout, delay, future_id)

        await future
        self._set_futures -= 1
        return future.result()

    def _process_timeout(self, message: Message) -> Tuple[bool, int]:
        if isinstance(message, Timeout):
            self._futures[message.parameter].set_result(message.start_time + message.duration)
        # Timeout is processed instantly
        return True, 0

    def is_composite(self, id: int) -> bool:
        return id in self._messages

    def incoming_message(self, message: Message) -> None:
        self._incoming_queue.add(message)

    async def send_request(self, request: Request):
        self._log.debug(f"[start] Composite action: sending message with id {request.id}")
        self._messages.add(request.id)
        self._msg.send_message(request)
        self._log.debug(f"[ end ] Composite action: sending message with id {request.id}")

    async def process_composite(self, request) -> None:
        self._log.debug(f"[start] Composite action: processing request from composite queue: {request}")
        delay, response = await self._coroutines[request.id]
        del self._coroutines[request.id]

        # If the complex message was the top-level one, return the result to a service
        if request.id in self._futures:
            self._futures[request.id].set_result(response)
        else:
            caller_id = request.platform_specific["caller_id"]
            service = self._general.get_object_by_id(caller_id, Service)
            service.active_service.process_message(response)
        self._log.debug(f"[ end ] Composite action: processing request from composite queue. Got this response: {response}")
        self._composites_processing -= 1

    async def process(self) -> [bool, bool]:
        while self._composite_queue:
            request = self._composite_queue.pop()
            self._loop.create_task(self.process_composite(request))
            self._composites_processing += 1

        while self._outgoing_queue:
            request = self._outgoing_queue.pop()
            self._log.debug(f"[start] Composite action: processing request from outgoing queue: {request}")
            await self._loop.create_task(self.send_request(request))
            self._log.debug(f"[ end ] Composite action: processing request from outgoing queue: {request}")

        while self._incoming_queue:
            response = self._incoming_queue.pop()
            self._log.debug(f"[start] Composite queue: processing response from incoming queue: {response}")
            self._futures[response.id].set_result(response)
            self._log.debug(f"[ end ] Composite queue: processing response from incoming queue: {response}")

        if self._composites_processing > 0:
            # Yield control to composite tasks processing, just to be sure it does not get starved.
            await asyncio.sleep(0)

        # Indicate we have something to process if there is anything in queues. By the nature of the code above, when
        # these queues are empty then everything should either be resolved or stuck in an await.
        return bool(self._composite_queue) or bool(self._outgoing_queue) or bool(self._incoming_queue), self._composites_processing > 0
