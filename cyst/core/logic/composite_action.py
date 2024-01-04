import asyncio

from typing import Dict

from cyst.api.environment.message import Request, Response, Message
from cyst.api.logic.behavioral_model import BehavioralModel
from cyst.api.logic.composite_action import CompositeActionManager

from cyst.core.environment.environment import EnvironmentMessagingImpl, EnvironmentResources
from cyst.core.logic.action import ActionImpl, ActionType


class CompositeActionManagerImpl(CompositeActionManager):
    def __init__(self, behavioral_models: Dict[str, BehavioralModel], messaging: EnvironmentMessagingImpl, resources: EnvironmentResources):
        self._loop = asyncio.new_event_loop()
        self._futures = {}
        self._incoming_queue = set()
        self._outgoing_queue = set()
        self._composite_queue = set()
        self._coroutines = {}
        self._models = behavioral_models
        self._msg = messaging
        self._res = resources
        self._processing = False
        self._messages = set()
        self._set_futures = 0

    def processing(self) -> bool:
        # If we are waiting for something to finish, we are processing
        return bool(self._incoming_queue or self._outgoing_queue or self._composite_queue or self._set_futures > 0)

    def execute_request(self, request: Request, delay: int) -> None:
        self._coroutines[request.id] = self._models[request.action.namespace].action_flow(request)
        self._composite_queue.add(request)

    async def call_action(self, request: Request, delay: int) -> None:
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

    def delay(self, delay: int) -> None:
        pass

    def is_composite(self, id: int) -> bool:
        return id in self._messages

    def is_top_level(self, id: int) -> bool:
        return id not in self._futures

    def incoming_message(self, message: Message) -> None:
        self._incoming_queue.add(message)

    async def send_request(self, request: Request):
        print(f"[start: {self._res.clock.simulation_time()}] Sending message with id {request.id}")
        self._messages.add(request.id)
        self._msg.send_message(request)
        print(f"[ end : {self._res.clock.simulation_time()}] Sending message with id {request.id}")

    def process(self, time: int) -> None:
        while self._outgoing_queue or self._composite_queue or self._processing or self._incoming_queue or self._set_futures > 0:
            self._loop.create_task(self._process(time))
            self._loop.call_soon(self._loop.stop)
            self._loop.run_forever()

        # Realistically, we need some more loop steps to serve the awaits when all futures are set
        # The number 4 was chosen because it works and gives also a hefty margin. As far as I checked, 1 is enough.
        for _ in range(4):
            self._loop.create_task(self._process(time))
            self._loop.call_soon(self._loop.stop)
            self._loop.run_forever()

    async def _process(self, time: int) -> None:
        if self._composite_queue:
            request = self._composite_queue.pop()
            print(f"[start: {self._res.clock.simulation_time()}] Processing request from composite queue: {request}")
            self._processing = True
            delay, response = await self._loop.create_task(self._coroutines[request.id])
            # Composite message is processed, remove it from the system
            del self._coroutines[request.id]
            # Send the result to the caller
            self._msg.send_message(response, delay)
            self._processing = False
            print(f"[ end : {self._res.clock.simulation_time()}] Processing request from composite queue: {request}")

        if self._outgoing_queue:
            request = self._outgoing_queue.pop()
            print(f"[start: {self._res.clock.simulation_time()}] Processing request from outgoing queue: {request}")
            self._processing = True
            await self._loop.create_task(self.send_request(request))
            self._processing = False
            print(f"[ end : {self._res.clock.simulation_time()}] Processing request from outgoing queue: {request}")

        if self._incoming_queue:
            response = self._incoming_queue.pop()
            print(f"[start: {self._res.clock.simulation_time()}] Processing response from incoming queue: {response}")
            self._set_futures += 1
            self._futures[response.id].set_result(response)
            print(f"[ end : {self._res.clock.simulation_time()}] Processing response from incoming queue: {response}")
