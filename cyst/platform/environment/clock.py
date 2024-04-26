from datetime import datetime
from typing import Any

from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import Clock
from cyst.api.host.service import ActiveService


class SimulationClock(Clock):
    def __init__(self, messaging: EnvironmentMessaging):
        self._time = 0
        self._messaging = messaging

    def current_time(self) -> float:
        return self._time

    def real_time(self) -> datetime:
        pass

    def advance_time(self, delta: float) -> float:
        if delta >= 0:
            self._time += delta
        return self._time

    def timeout(self, service: ActiveService, delay: int, content: Any) -> None:
        # TODO: Create a timeout message
        pass