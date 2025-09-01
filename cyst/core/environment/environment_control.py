from __future__ import annotations

import asyncio
import uuid
import time

from contextlib import suppress
from typing import Tuple, TYPE_CHECKING

from cyst.api.environment.control import EnvironmentState, EnvironmentControl
from cyst.api.environment.message import ComponentState
from cyst.api.environment.platform_specification import PlatformType
from cyst.api.environment.stats import Statistics
from cyst.api.host.service import ServiceState

from cyst.core.environment.serialization import Serializer
from cyst.core.environment.stats import StatisticsImpl

if TYPE_CHECKING:
    from cyst.core.environment.environment import _Environment


class EnvironmentControlImpl(EnvironmentControl):
    def __init__(self, env: _Environment):
        self._env = env

    @property
    def state(self) -> EnvironmentState:
        return _state(self._env)

    def init(self) -> Tuple[bool, EnvironmentState]:
        return _init(self._env)

    def commit(self) -> None:
        return _commit(self._env)

    def reset(self, run_id: str = str(uuid.uuid4())) -> Tuple[bool, EnvironmentState]:
        return _reset(self._env, run_id)

    def run(self) -> Tuple[bool, EnvironmentState]:
        return _run(self._env)

    def pause(self) -> Tuple[bool, EnvironmentState]:
        return _pause(self._env)

    def terminate(self) -> Tuple[bool, EnvironmentState]:
        return _terminate(self._env)

    def add_pause_on_request(self, id: str) -> None:
        return _add_pause_on_request(self._env, id)

    def remove_pause_on_request(self, id: str) -> None:
        return _remove_pause_on_request(self._env, id)

    def add_pause_on_response(self, id: str) -> None:
        return _add_pause_on_response(self._env, id)

    def remove_pause_on_response(self, id: str) -> None:
        return _remove_pause_on_response(self._env, id)

    def snapshot_save(self) -> str:
        return _snapshot_save(self._env)

    def snapshot_load(self, state: str) -> None:
        return _snapshot_load(self._env, state)

    def transaction_start(self) -> Tuple[int, int, str]:
        return _transaction_start(self._env)

    def transaction_commit(self, transaction_id: int) -> Tuple[bool, str]:
        return _transaction_commit(self._env, transaction_id)

    def transaction_rollback(self, transaction_id: int) -> Tuple[bool, str]:
        return _transaction_rollback(self._env, transaction_id)


# ----------------------------------------------------------------------------------------------------------------------
# Free function implementations of the above class. It is being done this way to shut up the type checking and to
# overcome python's limitation on having a class implemented in multiple files.
def _state(self: _Environment) -> EnvironmentState:
    return self._state


def _init(self: _Environment) -> Tuple[bool, EnvironmentState]:
    if self._initialized:
        return True, self._state

    if self._state == EnvironmentState.RUNNING or self._state == EnvironmentState.PAUSED:
        return False, self._state

    self._pause = False
    self._terminate = False
    self._state = EnvironmentState.INIT

    # Set basic statistics
    s = StatisticsImpl.cast_from(self.infrastructure.statistics)
    s.configuration_id = self._runtime_configuration.config_id
    s.start_time_real = time.time()

    # Initialize the platform, if needed
    if self._platform:
        self._platform.init()

    self._initialized = True

    return True, self._state


def _reset(self: _Environment, run_id: str = str(uuid.uuid4())) -> Tuple[bool, EnvironmentState]:
    if self._state != EnvironmentState.FINISHED and self._state != EnvironmentState.TERMINATED:
        return False, self._state

    self._network.reset()
    self._time = 0
    self._start_time = time.localtime()
    self._message_queue.clear()
    self._pause = False
    self._terminate = False
    self._run_id = run_id
    self._state = EnvironmentState.INIT

    return True, self._state

def _run(self: _Environment) -> Tuple[bool, EnvironmentState]:

    if not self._initialized:
        return False, self._state

    # if paused, unpause
    if self._state == EnvironmentState.PAUSED:
        self._pause = False

    # Run
    self._finish = False

    service_run_tasks = set()
    # As a first thing after init, we run all the services (and make sure we don't run it multiple times)
    if self._state == EnvironmentState.INIT and len(service_run_tasks) == 0:
        for service in self._service_store.get_active_services():
            t = self._loop.create_task(service.run())
            service_run_tasks.add(t)
            t.add_done_callback(service_run_tasks.discard)

    while not (self._pause or self._finish or self._terminate):
        # Make sure to not terminate the pump before the run() methods finish
        if self._state == EnvironmentState.INIT:
            if len(service_run_tasks) == 0:
                self._state = EnvironmentState.RUNNING

        # And now we are finally doing the ordinary stuff
        t = self._loop.create_task(self._process_async())
        self._loop.call_soon(self._loop.stop)
        self._loop.run_forever()

    if self._pause:
        self._state = EnvironmentState.PAUSED
    else:
        # Send a notification to all active services that we had to terminate
        effect_description = ""
        # Terminate description has a priority
        if self._terminate and self._terminate_reason:
            effect_description = self._terminate_reason
        if not effect_description and self._finish and self._finish_reason:
            effect_description = self._finish_reason

        end_signal = self.messaging.create_signal(signal_origin="__environment",
                                                  state=ComponentState.TERMINATED if self._terminate else ComponentState.FINISHED,
                                                  effect_origin="__environment",
                                                  effect_description=effect_description)

        for service in self._service_store.get_active_services():
            self._loop.create_task(service.process_message(end_signal))

        self._data_store.add_signal(end_signal)

        # Realistically, we need some more loop steps to serve the awaits when all futures are set
        # The number 4 was chosen because it works and gives also a hefty margin. As far as I checked, 1 is enough.
        for _ in range(4):
            self._loop.create_task(self._process_async())
            self._loop.call_soon(self._loop.stop)
            self._loop.run_forever()

        # Terminate clears the task queue and sets the clock back to zero
        if self._terminate:
            self._state = EnvironmentState.TERMINATED
            self._time = 0
            self._message_queue.clear()

        else:
            self._state = EnvironmentState.FINISHED

        # Clear the loop if there are any outstanding tasks
        pending = asyncio.all_tasks(self._loop)
        for task in pending:
            task.cancel()

            with suppress(asyncio.CancelledError):
                self._loop.run_until_complete(task)

    return True, self._state


def _pause(self: _Environment) -> Tuple[bool, EnvironmentState]:

    if self._state != EnvironmentState.RUNNING:
        return False, self._state

    self._pause = True
    # This will return True + running state, but it will be returned to an actor other than the one who called
    # Environment.run() in the first place. Or I hope so...
    return True, self._state


def _terminate(self: _Environment) -> Tuple[bool, EnvironmentState]:

    self._terminate = True
    self._terminate_reason = "Direct call to environment terminate method."

    if self._platform:
        self._platform.terminate()

    return True, self._state


def _commit(self: _Environment) -> None:
    s = StatisticsImpl.cast_from(self.infrastructure.statistics)
    s.end_time_real = time.time()
    s.end_time_virtual = self._time

    self._data_store.add_statistics(self.infrastructure.statistics)

    # TODO: What?
    if self._platform:
        self._platform.terminate()

    if self._runtime_configuration.data_batch_storage and self._runtime_configuration.data_backend != "memory":
        memory = self._data_store.memory

        self._data_store_batch.add_signal(*memory["signals"])
        self._data_store_batch.add_statistics(memory["statistics"])
        self._data_store_batch.add_action(*memory["actions"])
        self._data_store_batch.add_message(*memory["messages"])


def _add_pause_on_request(self: _Environment, id: str) -> None:
    self._pause_on_request.append(id)


def _remove_pause_on_request(self: _Environment, id: str) -> None:
    self._pause_on_request = [x for x in self._pause_on_request if x != id]


def _add_pause_on_response(self: _Environment, id: str) -> None:
    self._pause_on_response.append(id)


def _remove_pause_on_response(self: _Environment, id: str) -> None:
    self._pause_on_response = [x for x in self._pause_on_response if x != id]


def _snapshot_save(self: _Environment) -> str:
    return Serializer.serialize(self)


def _snapshot_load(self: _Environment, state: str) -> None:
    self._replace(Serializer.deserialize(state))


def _transaction_start(self: _Environment) -> Tuple[int, int, str]:
    return (0, 0, "")


def _transaction_commit(self: _Environment, transaction_id: int) -> Tuple[bool, str]:
    return (True, "")


def _transaction_rollback(self: _Environment, transaction_id: int) -> Tuple[bool, str]:
    return (True, "")
