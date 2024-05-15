from __future__ import annotations

import asyncio
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

from cyst.core.environment.stats import StatisticsImpl
from cyst.core.environment.stores import ActionStoreImpl, ServiceStoreImpl, ExploitStoreImpl
from cyst.core.environment.external_resources import ExternalResourcesImpl

if TYPE_CHECKING:
    from cyst.core.environment.environment import _Environment


# ----------------------------------------------------------------------------------------------------------------------
class EnvironmentResourcesImpl(EnvironmentResources):
    def __init__(self, env: _Environment, platform: Optional[PlatformSpecification] = None):
        self._env = env
        self._action_store = ActionStoreImpl(platform)
        self._exploit_store = ExploitStoreImpl()
        self._clock = None
        self._statistics = StatisticsImpl()
        self._external_resources = None

    def init_resources(self, loop: asyncio.AbstractEventLoop, clock: Clock):
        self._clock = clock
        self._external_resources = ExternalResourcesImpl(loop, clock)

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
