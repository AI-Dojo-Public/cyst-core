from datetime import datetime
from typing import Any, Union, Callable

from cyst.api.environment.message import Timeout
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import Clock
from cyst.api.host.service import ActiveService

from cyst.platform.environment.message import TimeoutImpl

class SimulationClock(Clock):
    def __init__(self, messaging: EnvironmentMessaging):
        self._time = 0
        self._messaging = messaging

    def current_time(self) -> float:
        return self._time

    def real_time(self) -> datetime:
        raise NotImplementedError()

    def timeout(self, callback: Union[ActiveService, Callable[[Timeout], None]], delay: float, parameter: Any = None) -> None:
        timeout = TimeoutImpl(callback, self._time, delay, parameter)
        self._messaging.send_message(timeout, int(delay))
