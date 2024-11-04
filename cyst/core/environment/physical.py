from datetime import datetime
from typing import List

from cyst.api.environment.physical import PhysicalAccess, PhysicalLocation, PhysicalConnection
from cyst.api.utils.duration import Duration


class PhysicalAccessImpl(PhysicalAccess):
    def __init__(self, identity: str, time_from: datetime | None = None, time_to: datetime | None = None):
        self._identity = identity
        self._time_from = time_from
        self._time_to = time_to

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def time_from(self) -> datetime | None:
        return self._time_from

    @property
    def time_to(self) -> datetime | None:
        return self._time_to


class PhysicalLocationImpl(PhysicalLocation):
    def __init__(self):
        self._assets = []
        self._access = []

    @property
    def assets(self) -> List[str]:
        return self._assets

    @property
    def access(self) -> List[PhysicalAccess]:
        return self._access

    def add_asset(self, asset_id: str) -> None:
        if asset_id not in self._assets:
            self._assets.append(asset_id)

    def remove_asset(self, asset_id: str) -> None:
        if asset_id in self._assets:
            self._assets.remove(asset_id)

    def add_access(self, access: PhysicalAccess) -> None:
        self._access.append(access)

    def remove_access(self, access: PhysicalAccess) -> None:
        if access in self._access:
            self._access.remove(access)

class PhysicalConnectionImpl(PhysicalConnection):
    def __init__(self, origin: str, destination: str, travel_time: Duration):
        self._origin = origin
        self._destination = destination
        self._travel_time = travel_time

    @property
    def origin(self) -> str:
        return self._origin

    @property
    def destination(self) -> str:
        return self._destination

    @property
    def travel_time(self) -> Duration:
        return self._travel_time