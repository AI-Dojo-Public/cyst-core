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
        self._subordinate_action_counts = {}
        self._task_parents = {}
        self._composites_processing = 0

        self._loop.set_task_factory(self.task_factory)

    def clear_resource_task(self, task: asyncio.Task):
        task_name = task.get_name()
        parent_task = self._task_parents[task_name]
        self._subordinate_action_counts[parent_task] -= 1

    def task_factory(self, loop: asyncio.AbstractEventLoop, coro, context = None) -> asyncio.Task:
        task = asyncio.Task(coro=coro, loop=loop)

        # We really hijack the task creation only to get access to call_action parent
        if coro.cr_code.co_name == "call_action":
            task_name = asyncio.current_task().get_name()
            self._task_parents[task.get_name()] = task_name
            self._subordinate_action_counts[task_name] += 1

        # External resource tasks are a bit different, mainly because we need to take care of them only if they are
        # executed in the context of a composite action
        if coro.cr_code.co_name == "send" or coro.cr_code.co_name == "receive":
            task_name = asyncio.current_task().get_name()
            if task_name in self._subordinate_action_counts:
                self._task_parents[task.get_name()] = task_name
                self._subordinate_action_counts[task_name] += 1
                task.add_done_callback(self.clear_resource_task)

        return task

    def execute_request(self, request: Request, delay: int) -> None:
        self._composite_queue.add(request)
        self._coroutines[request.id] = self._models[request.action.namespace].action_flow(request)

    async def call_action(self, request: Request, delay: float = 0.0) -> None:
        task_name = asyncio.current_task().get_name()

        if task_name in self._subordinate_action_counts:
            self._subordinate_action_counts[task_name] += 1

        future = self._loop.create_future()
        self._futures[request.id] = future

        if ActionImpl.cast_from(request.action).type == ActionType.COMPOSITE:
            self._composite_queue.add(request)
            self._coroutines[request.id] = self._models[request.action.namespace].action_flow(request)
        else:
            self._outgoing_queue.add(request)

        await future

        if task_name in self._task_parents:
            self._subordinate_action_counts[self._task_parents[task_name]] -= 1
            del self._task_parents[task_name]
        else:
            self._subordinate_action_counts[task_name] -= 1

        return future.result()

    async def delay(self, delay: float = 0.0) -> None:
        future = self._loop.create_future()
        future_id = uuid4()
        self._futures[future_id] = future

        self._res.clock.timeout(self._process_timeout, delay, future_id)

        task_name = asyncio.current_task().get_name()
        if task_name in self._subordinate_action_counts:
            self._subordinate_action_counts[task_name] += 1

        await future
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
        self._log.debug(f"[time: {self._res.clock.current_time()}][start] Composite action: sending message with id {request.id}")
        self._messages.add(request.id)
        self._msg.send_message(request)
        self._log.debug(f"[time: {self._res.clock.current_time()}][ end ] Composite action: sending message with id {request.id}")

    async def process_composite(self, request) -> None:
        self._log.debug(f"[time: {self._res.clock.current_time()}][start] Composite action: processing request from composite queue: {request}")

        task_name = asyncio.current_task().get_name()
        self._subordinate_action_counts[task_name] = 0

        delay, response = await self._coroutines[request.id]
        del self._coroutines[request.id]

        # If the complex message was the top-level one, return the result to a service
        if request.id in self._futures:
            self._futures[request.id].set_result(response)
        else:
            caller_id = request.platform_specific["caller_id"]
            service = self._general.get_object_by_id(caller_id, ActiveService)
            await service.process_message(response)

        self._composites_processing -= 1
        self._log.debug(f"[time: {self._res.clock.current_time()}][ end ] Composite action: processing request from composite queue. Got this response: {response}")
        del self._subordinate_action_counts[asyncio.current_task().get_name()]

    async def process(self) -> [bool, bool, bool]:
        while self._composite_queue:
            request = self._composite_queue.pop()
            self._loop.create_task(self.process_composite(request))
            self._composites_processing += 1

        while self._outgoing_queue:
            request = self._outgoing_queue.pop()
            self._log.debug(f"[time: {self._res.clock.current_time()}][start] Composite action: processing request from outgoing queue: {request}")
            await self._loop.create_task(self.send_request(request))
            self._log.debug(f"[time: {self._res.clock.current_time()}][ end ] Composite action: processing request from outgoing queue: {request}")

        while self._incoming_queue:
            response = self._incoming_queue.pop()
            self._log.debug(f"[time: {self._res.clock.current_time()}][start] Composite queue: processing response from incoming queue: {response}")
            self._futures[response.id].set_result(response)
            self._log.debug(f"[time: {self._res.clock.current_time()}][ end ] Composite queue: processing response from incoming queue: {response}")

        # This is more important than it looks!
        if self._composites_processing > 0:
            # Yield control to composite tasks processing, just to be sure it does not get starved.
            await asyncio.sleep(0)

        # Indicate we have something to process if there is anything in queues. By the nature of the code above, when
        # these queues are empty then everything should either be resolved or stuck in an await.
        composite_actions_resolving = False
        for actions_remaining in self._subordinate_action_counts.values():
            if actions_remaining == 0:
                composite_actions_resolving = True
                break

        return bool(self._composite_queue) or bool(self._outgoing_queue) or bool(self._incoming_queue), composite_actions_resolving, self._composites_processing > 0
