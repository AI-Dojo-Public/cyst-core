from abc import ABC, abstractmethod
from datetime import datetime
from deprecated.sphinx import versionadded
from typing import Any

from cyst.api.host.service import ActiveService


class Clock(ABC):
    """ Clock interface provides access to time management of a given platform.
    """
    @versionadded(version="0.6.0")
    @abstractmethod
    def current_time(self) -> float:
        """ Returns a current time of a platform as an offset from a specific time in the past. In case of a discrete
        simulation platform, it will return a whole number. For real-time environments, this will be a fractional
        number (aka. python's time() function).

        :return: Current time as an offset.
        """

    @versionadded(version="0.6.0")
    @abstractmethod
    def real_time(self) -> datetime:
        """ Returns a current time of a platform converted to a real date-time information. In case of a discrete
        simulation platform this entails a conversion of time offset to a real time. In case o a rel-time environment
        this will likely be only a reading of a system clock.

        :return: Current time as a datetime structure.
        """

    @versionadded(version="0.6.0")
    @abstractmethod
    def advance_time(self, delta: float) -> float:
        """
        Orders the platform to advance time by the specified delta. The platform, especially the one operating in the
        emulated mode, is free to ignore this request.

        :param delta: The amount of time units the time should advance. If set to zero or less, the call is ignored
            because the clock are assumed to be monotonic.
        :type delta: float

        :return: A time after advancing in clock's own units.
        """

    @abstractmethod
    def timeout(self, service: ActiveService, delay: int, content: Any) -> None:
        """ Schedule a timeout message for a given service. This acts like a time callback and enables inclusion of
        any kind of data.

        :param service: The service, which should receive the timeout message.
        :param delay: The duration of the timeout in simulation time.
        :param content: The included data. They will not be modified.
        :return: None
        """
