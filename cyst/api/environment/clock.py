from abc import ABC, abstractmethod
from datetime import datetime
from deprecated.sphinx import versionadded, versionchanged
from typing import Any, Union, Callable, Tuple

from cyst.api.environment.message import Message
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
        simulation platform this entails a conversion of time offset to a real time. In case o a real-time environment
        this will likely be only a reading of a system clock.

        :return: Current time as a datetime structure.
        """

    @versionchanged(version="0.6.0", reason="Changed delay type to float and added support for generic callbacks.")
    @abstractmethod
    def timeout(self, callback: Union[ActiveService, Callable[[Message], Tuple[bool, int]]], delay: float, parameter: Any = None) -> None:
        """ Schedule a timeout message. This acts like a time callback and enables inclusion of any kind of data.

        :param callback: Either a service, which should receive the timeout message, or an arbitrary callback.
        :param delay: The duration of the timeout in simulation time.
        :param parameter: The included data. They will not be modified.
        :return: None
        """
