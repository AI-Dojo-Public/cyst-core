from abc import ABC, abstractmethod
from time import struct_time
from typing import Any

from cyst.api.host.service import ActiveService


class Clock(ABC):
    """ Clock interface provides an access to reading the simulation time. It can also be used to set a timeout for a
    service.
    """
    @abstractmethod
    def simulation_time(self) -> int:
        """ Returns a current time of simulation in internal simulation units.

        :return: Simulation time.
        """

    @abstractmethod
    def hybrid_time(self) -> struct_time:
        """ Returns a current time of simulation in pseudo-real time, which is calculated as a base time, given during
        initialization + (clock factor * simulation time).

        :return: Simulation time.
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
