from dataclasses import field
from datetime import datetime, time
from typing import List, Tuple, Dict, Any
from uuid import uuid4

from cyst.api.environment.configuration import PhysicalConfiguration
from cyst.api.environment.environment import Environment
from cyst.api.environment.physical import PhysicalAccess, PhysicalLocation, PhysicalConnection
from cyst.api.network.node import Node
from cyst.api.utils.duration import Duration
from cyst.core.environment.physical import PhysicalAccessImpl, PhysicalConnectionImpl, PhysicalLocationImpl
from cyst.platform.network.router import Router


class PhysicalConfigurationImpl(PhysicalConfiguration):
    def __init__(self, env: Environment):
        self.env = env
        self._locations: Dict[str, PhysicalLocation] = {}
        self._connections: Dict[Tuple[str, str], PhysicalConnection] = {}

    def create_physical_location(self, location_id: str | None) -> PhysicalLocation:
        location = PhysicalLocationImpl()
        if location_id is None:
            location_id = field(default_factory=lambda: str(uuid4()))
        self._locations[location_id] = location
        return location

    def get_physical_location(self, location_id: str) -> PhysicalLocation | None:
        return self._locations.get(location_id)

    def get_physical_locations(self) -> List[PhysicalLocation]:
        return list(self._locations.values())

    def remove_physical_location(self, location_id: str) -> None:
        if location_id not in self._locations:
            raise ValueError(f"Location '{location_id}' does not exist.")

        del self._locations[location_id]
        self._connections = {
            k: v for k, v in self._connections.items()
            if k[0] != location_id and k[1] != location_id
        }

    def create_physical_access(self, identity: str, time_from: datetime | None, time_to: datetime | None) -> PhysicalAccess:
        return PhysicalAccessImpl(identity=identity, time_from=time_from, time_to=time_to)

    def add_physical_access(self, location_id: str, access: PhysicalAccess) -> None:
        location = self.get_physical_location(location_id)
        if not location:
            raise ValueError(f"Location '{location_id}' does not exist.")
        location.access.append(access)

    def get_physical_accesses(self, location_id: str) -> List[PhysicalAccess]:
        location = self.get_physical_location(location_id)
        if not location:
            raise ValueError(f"Location '{location_id}' does not exist.")
        return location.access

    def remove_physical_access(self, location_id: str, access: PhysicalAccess) -> None:
        location = self.get_physical_location(location_id)
        if not location:
            raise ValueError(f"Location '{location_id}' does not exist.")
        location.access.remove(access)

    def add_physical_connection(self, origin: str, destination: str, travel_time: Duration) -> None:
        if origin not in self._locations:
            raise ValueError(f"Origin location '{origin}' does not exist.")
        if destination not in self._locations:
            raise ValueError(f"Destination location '{destination}' does not exist.")

        if (origin, destination) in self._connections or (destination, origin) in self._connections:
            return

        connection = PhysicalConnectionImpl(origin=origin, destination=destination, travel_time=travel_time)
        self._connections[(origin, destination)] = connection

    def remove_physical_connection(self, origin: str, destination: str) -> None:
        if origin not in self._locations:
            raise ValueError(f"Origin location '{origin}' does not exist.")
        if destination not in self._locations:
            raise ValueError(f"Destination location '{destination}' does not exist.")

        if (origin, destination) in self._connections:
            self._connections.pop((origin, destination), None)
        elif (destination, origin) in self._connections:
            self._connections.pop((destination, origin), None)


    def get_physical_connections(self, origin: str, destination: str | None) -> List[PhysicalConnection]:
        if origin not in self._locations:
            raise ValueError(f"Origin location '{origin}' does not exist.")
        if destination is not None and destination not in self._locations:
            raise ValueError(f"Destination location '{destination}' does not exist.")

        if destination:
            return [self._connections.get((origin, destination)) or self._connections.get((destination, origin))]
        return [
            conn for (orig, dest), conn in self._connections.items()
            if orig == origin or dest == origin
        ]

    def place_asset(self, location_id: str, asset: str) -> None:
        location = self.get_physical_location(location_id)
        if not location:
            raise ValueError(f"Location '{location_id}' does not exist.")

        current_location = self.get_location(asset)
        if current_location and current_location != location_id:
            self._locations[current_location].assets.remove(asset)
        elif current_location and current_location == location_id:
            return

        location.assets.append(asset)

    def remove_asset(self, location_id: str, asset: str) -> None:
        location = self.get_physical_location(location_id)
        if not location:
            raise ValueError(f"Location '{location_id}' does not exist.")

        if asset in location.assets:
            location.assets.remove(asset)

    def move_asset(self, origin: str, destination: str, asset: str) -> Tuple[bool, str, str]:
        if origin not in self._locations:
            raise ValueError(f"Origin location '{origin}' does not exist.")
        if destination not in self._locations:
            raise ValueError(f"Destination location '{destination}' does not exist.")

        if (origin, destination) not in self._connections and (destination, origin) not in self._connections:
            return False, origin, "No connection between locations"

        if asset not in self._locations[origin].assets:
            return False, "", "Asset not in origin location"

        try:
            self.env.configuration.general.get_object_by_id(asset, Node)
            asset_type = "Node"
        except KeyError or AttributeError:
            try:
                self.env.configuration.general.get_object_by_id(asset, Router)
                asset_type = "Router"
            except KeyError or AttributeError:
                asset_type = "User"

        # TODO determine if the asset is user by asking user manager, instead of this try-except block
        if asset_type == "User":
            access_rights = self.get_physical_accesses(destination)
            real_time = self.env.resources.clock.real_time().time()
            has_access = False

            for access in access_rights:
                identity_matches = access.identity in {asset, "*"}

                start_time = access.time_from.time() if access.time_from else time(0, 0, 0)
                end_time = access.time_to.time() if access.time_to else time(23, 59, 59)
                time_in_range = start_time <= real_time <= end_time

                if identity_matches and time_in_range:
                    has_access = True
                    break

            if not has_access:
                return False, origin, "User lacks access rights at the destination."

        self.remove_asset(origin, asset)
        self.place_asset(destination, asset)
        return True, destination, ""


    def get_assets(self, location_id: str) -> List[str]:
            location = self.get_physical_location(location_id)
            if not location:
                raise ValueError(f"Location '{location_id}' does not exist.")
            return location.assets

    def get_location(self, asset: str) -> str:
        for location_id, location in self._locations.items():
            if asset in location.assets:
                return location_id
        return ""

