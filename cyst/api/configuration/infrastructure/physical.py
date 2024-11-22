from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.utils.duration import Duration


@dataclass
class PhysicalAccessConfig(ConfigItem):
    """
    Physical access configuration specifies, which user can access given physical location in a given time. The access
    control works in a default deny mode, i.e., unless the user is cleared for access, the physical location is
    off-limits.

    :param identity: A unique identifier of a user. An asterisk '*' can be used to denote that this configuration
        applies to any user.
    :type identity: str

    :param time_from: A specification of a time of a day (the date part is ignored) from which the access is granted.
        If no time is provided, then 00:00:00 is assumed.
    :type time_from: datetime | None

    :param time_to: A specification of a time of a day (the date part is ignored) to which the access is granted.
        If no time is provided, then 23:59:59 is assumed.
    :type time_to: datetime | None
    """
    identity: str
    time_from: datetime | None
    time_to: datetime | None
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__physical_access"
    id: str = ""


@dataclass
class PhysicalLocationConfig(ConfigItem):
    """
    Physical location groups together physical assets, which will most often be Nodes and Routers. While Connections
    have their physical manifestations, they are not considered physical for this purpose.

    :param assets: A list of items that are physically present at a given location. This is represented as a list of
        their IDs in the configuration.
    :type assets: List[str]

    :param access: A list of physical access configurations.
    :type access: List[PhysicalAccessConfig]

    """
    assets: List[str]
    access: List[PhysicalAccessConfig]
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__physical_location"
    id: str = ""


@dataclass
class PhysicalConnectionConfig(ConfigItem):
    """
    Physical connection represents traversing between two locations. This can be anything from going through a door
    frame to boarding an intercontinental flight. Physical connections do not have access control, i.e., any user can
    attempt to cross the divide between two locations, but if they are denied access at the destination, it is assumed
    that the user will have to return back effectively wasting twice the time without accomplishing nothing.

    Physical connections are bidirectional, so there is no real difference between the origin and destination.

    N.B.: Situation when a user can have access to an infrastructure via wireless networks when travelling between
    locations is currently not considered.

    :param origin: An id of the first location.
    :type origin: str

    :param destination: An id of the second location.
    :type destination: str

    :param travel_time: A time needed to traverse the physical connection.
    :type travel_time: Duration

    """
    origin: str
    destination: str
    travel_time: Duration
    ref: str = field(default_factory=lambda: str(uuid4()))
    name: str = "__physical_connection"
    id: str = ""
