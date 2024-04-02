from __future__ import annotations

from datetime import datetime
from heapq import heappush
from time import struct_time, localtime
from typing import TYPE_CHECKING, Any, Optional

from cyst.api.environment.external import ExternalResources
from cyst.api.environment.clock import Clock
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.platform import PlatformSpecification
from cyst.api.environment.stats import Statistics
from cyst.api.environment.stores import ExploitStore, ActionStore
from cyst.api.host.service import ActiveService
from cyst.api.utils.counter import Counter

from cyst.core.environment.message import TimeoutImpl
from cyst.core.environment.stats import StatisticsImpl
from cyst.core.environment.stores import ActionStoreImpl, ServiceStoreImpl, ExploitStoreImpl
from cyst.core.environment.external_resources import ExternalResourcesImpl

if TYPE_CHECKING:
    from cyst.core.environment.environment import _Environment


# ----------------------------------------------------------------------------------------------------------------------
class _Clock(Clock):
    def __init__(self, env: _Environment):
        self._env = env

    def current_time(self) -> float:
        return _simulation_time(self._env)

    def advance_time(self, delta: float) -> float:
        return _advance_time(self._env, delta)

    def real_time(self) -> datetime:
        pass

    def timeout(self, service: ActiveService, delay: int, content: Any) -> None:
        return _timeout(self._env, service, delay, content)


def _simulation_time(self: _Environment) -> int:
    return self._time


def _advance_time(self: _Environment, delta: float) -> float:
    self._time += int(delta)
    return float(self._time)

def _hybrid_time(self: _Environment) -> struct_time:
    # TODO this should be local time + self._time miliseconds
    return self._start_time


def _timeout(self: _Environment, service: ActiveService, delay: int, content: Any) -> None:
    m = TimeoutImpl(service, self._time, delay, content)
    heappush(self._message_queue, (self._time + delay, Counter().get("msg"), m))


# ----------------------------------------------------------------------------------------------------------------------
class EnvironmentResourcesImpl(EnvironmentResources):
    def __init__(self, env: _Environment, platform: Optional[PlatformSpecification] = None):
        self._env = env
        self._action_store = ActionStoreImpl(platform)
        self._exploit_store = ExploitStoreImpl()
        self._clock = _Clock(self._env)
        self._statistics = StatisticsImpl()
        self._external_resources = ExternalResourcesImpl(self._clock, env.add_resource_task_collection)

    @property
    def action_store(self) -> ActionStore:
        return self._action_store

    @property
    def exploit_store(self) -> ExploitStore:
        return self._exploit_store

    @property
    def clock(self) -> Clock:
        return self._clock

    @property
    def statistics(self) -> Statistics:
        return self._statistics

    @property
    def external(self) -> ExternalResources:
        return self._external_resources
