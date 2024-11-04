from abc import abstractmethod, ABC
from datetime import datetime
from typing import List

from cyst.api.utils.duration import Duration


class PhysicalAccess(ABC):
    """
    Physical access specifies, which user can access given physical location in a given time. The access
    control works in a default deny mode, i.e., unless the user is cleared for access, the physical location is
    off-limits.
    """

    @property
    @abstractmethod
    def identity(self) -> str:
        """
        :return: A unique identifier of a user. An asterisk '*' denotes that this access applies to any user.
        """

    @property
    @abstractmethod
    def time_from(self) -> datetime | None:
        """
        :return: A time of a day (the date part is ignored) from which the access is granted.
        """

    @property
    @abstractmethod
    def time_to(self) -> datetime | None:
        """
        :return: A time of a day (the date part is ignored) to which the access is granted.
        """


class PhysicalLocation:
    """
    Physical location groups together physical assets, which will most often be Nodes and Routers. While Connections
    have their physical manifestations, they are not considered physical for this purpose.
    """

    @property
    @abstractmethod
    def assets(self) -> List[str]:
        """
        A list of IDs of items that are physically present at a given location.

        :return: A list of asset IDs in the configuration.
        """

    @property
    @abstractmethod
    def access(self) -> List[PhysicalAccess]:
        """
        :return: A list of physical access specifications.
        """


class PhysicalConnection(ABC):
    """
    Physical connection represents traversing between two locations. This can be anything from going through a door
    frame to boarding an intercontinental flight. Physical connections do not have access control, i.e., any user can
    attempt to cross the divide between two locations, but if they are denied access at the destination, it is assumed
    that the user will have to return back effectively wasting twice the time without accomplishing nothing.

    Physical connections are bidirectional, so there is no real difference between the origin and destination.

    N.B.: Situation when a user can have access to an infrastructure via wireless networks when travelling between
    locations is currently not considered.
    """

    @property
    @abstractmethod
    def origin(self) -> str:
        """
        :return: An id of the first location.
        """

    @property
    @abstractmethod
    def destination(self) -> str:
        """
        :return: An id of the second location.
        """

    @property
    @abstractmethod
    def travel_time(self) -> Duration:
        """
        :return: A time needed to traverse the physical connection.
        """
