import unittest
from datetime import datetime

from netaddr import IPAddress, IPNetwork
from cyst.api.configuration.infrastructure.physical import PhysicalLocationConfig, PhysicalAccessConfig, \
    PhysicalConnectionConfig
from cyst.api.configuration.network.elements import ConnectionConfig, InterfaceConfig

from cyst.api.configuration.network.node import NodeConfig
from cyst.api.configuration.network.router import RouterConfig
from cyst.api.environment.environment import Environment
from cyst.api.environment.physical import PhysicalAccess, PhysicalLocation
from cyst.api.utils.duration import mins, Duration


node_1_id = "node_1"
node_1 = NodeConfig(
    active_services=[],
    passive_services=[],
    traffic_processors=[],
    shell="",
    interfaces=[InterfaceConfig(IPAddress("192.168.0.2"), IPNetwork("192.168.0.2/24"))],
    name=node_1_id)

node_2_id = "node_2"
node_2 = NodeConfig(
    active_services=[],
    passive_services=[],
    traffic_processors=[],
    shell="",
    interfaces=[InterfaceConfig(IPAddress("192.168.0.3"), IPNetwork("192.168.0.3/24"))],
    name=node_2_id)

router_id = "router"
router = RouterConfig(
    traffic_processors=[],
    interfaces=[
        InterfaceConfig(IPAddress("192.168.0.1"),
                        IPNetwork("192.168.0.0/24"),
                        index=0),
        InterfaceConfig(IPAddress("192.168.0.1"),
                        IPNetwork("192.168.0.0/24"),
                        index=1),
      ],
    name=router_id
)

connections_cfg = [
    ConnectionConfig(node_1, 0, router, 0),
    ConnectionConfig(node_2, 0, router, 1),
]

user_1_id = "user_1"
user_2_id = "user_2"
location_1_id = "location_1"
location_2_id = "location_2"
travel_time = mins(5)
time_from = datetime(year=2024, month=1, day=1, hour=8, minute=0, second=0)
time_to = datetime(year=2024, month=1, day=1, hour=16, minute=0, second=0)
time_out_of_access = datetime(year=2024, month=1, day=1, hour=20, minute=0, second=0)
time_inside_access = datetime(year=2024, month=1, day=1, hour=14, minute=0, second=0)
location_1_cfg = PhysicalLocationConfig(
    assets=[node_1_id, router_id],
    access=[],
    id=location_1_id,
)
location_2_cfg = PhysicalLocationConfig(
    assets=[node_2_id],
    access=[],
    id=location_2_id,
)

physical_connection = PhysicalConnectionConfig(origin=location_1_id, destination=location_2_id, travel_time=mins(2), id="physical_connection_1")

class TestPhysicalConfigurationImpl(unittest.TestCase):

    def setUp(self) -> None:
        self.config = Environment.create().configuration.physical
        self.location_1_id = "location_1"
        self.location_2_id = "location_2"
        self.user_1_id = "user_1"
        self.node_1_id = "node_1"
        self.node_2_id = "node_2"
        self.config.create_physical_location(self.location_1_id)
        self.config.create_physical_location(self.location_2_id)

    def test_0000_create_physical_location_creates_location_with_assets_and_access(self) -> None:
        location = self.config.create_physical_location(None)
        self.assertTrue(isinstance(location, PhysicalLocation), "New location has wrong type")
        self.assertEqual(len(location.assets), 0, "New location should have empty assets list")
        self.assertEqual(len(location.access), 0, "New location should have empty access list")

    def test_0001_get_physical_locations_returns_desired_location(self) -> None:
        location = self.config.get_physical_location(self.location_1_id)
        self.assertTrue(isinstance(location, PhysicalLocation),  "Retrieved location has wrong type")

    def test_0002_get_physical_locations_returns_none_for_nonexistent_location(self) -> None:
        location = self.config.get_physical_location("nonexistent_location")
        self.assertIsNone(location, "Nonexistent location is not None")

    def test_0003_get_physical_locations_returns_all_locations(self) -> None:
        locations = self.config.get_physical_locations()
        self.assertTrue(all(isinstance(loc, PhysicalLocation) for loc in locations), "Not all locations are of type PhysicalLocation")
        self.assertGreaterEqual(len(locations), 2, "Incorrect number of locations returned")

    def test_0004_remove_physical_location_removes_location(self) -> None:
        location_id = "temp_location"
        self.config.create_physical_location(location_id)
        self.config.remove_physical_location(location_id)
        location = self.config.get_physical_location(location_id)
        self.assertIsNone(location, "Location was not removed correctly")

    def test_0005_remove_physical_location_raises_error_for_nonexistent_location(self) -> None:
        nonexistent_location_id = "nonexistent_location"
        with self.assertRaises(ValueError) as context:
            self.config.remove_physical_location(nonexistent_location_id)
        self.assertEqual(
            str(context.exception),
            f"Location '{nonexistent_location_id}' does not exist.",
            "Error message does not match expected output for nonexistent location"
        )

    def test_0006_create_physical_access_creates_physical_access(self) -> None:
        access = self.config.create_physical_access(self.user_1_id, time_from, time_to)
        self.assertTrue(isinstance(access, PhysicalAccess),  "Retrieved access has wrong type")
        self.assertEqual(access.identity, self.user_1_id,  "Retrieved access has wrong identity")
        self.assertEqual(access.time_from, time_from,  "Retrieved access has wrong time_from")
        self.assertEqual(access.time_to, time_to,  "Retrieved access has wrong time_to")

    def test_0007_add_physical_access_adds_access_to_location(self) -> None:
        access = self.config.create_physical_access(self.user_1_id, time_from, time_to)
        self.config.add_physical_access(self.location_1_id, access)
        location = self.config.get_physical_location(self.location_1_id)
        self.assertIn(access, location.access, "Access was not added to location")

    def test_0008_add_physical_access_raises_error_for_nonexistent_location(self) -> None:
        nonexistent_location_id = "nonexistent_location"
        access = self.config.create_physical_access(self.user_1_id, time_from, time_to)

        with self.assertRaises(ValueError) as context:
            self.config.add_physical_access(nonexistent_location_id, access)

        self.assertEqual(
            str(context.exception),
            f"Location '{nonexistent_location_id}' does not exist.",
            "Error message does not match expected output for nonexistent location in add_physical_access"
        )

    def test_0009_get_physical_accesses_returns_all_accesses(self) -> None:
        access = self.config.create_physical_access(self.user_1_id, time_from, time_to)
        self.config.add_physical_access(self.location_1_id, access)

        accesses = self.config.get_physical_accesses(self.location_1_id)
        self.assertIsInstance(accesses, list, "Accesses should be a list")
        self.assertTrue(all(isinstance(acc, PhysicalAccess) for acc in accesses), "Not all accesses are of type PhysicalAccess")

    def test_0010_get_physical_accesses_raises_error_for_nonexistent_location(self) -> None:
        nonexistent_location_id = "nonexistent_location"

        with self.assertRaises(ValueError) as context:
            self.config.get_physical_accesses(nonexistent_location_id)

        self.assertEqual(
            str(context.exception),
            f"Location '{nonexistent_location_id}' does not exist.",
            "Error message does not match expected output for nonexistent location in get_physical_accesses"
        )

    def test_0011_remove_physical_access_removes_access_from_location(self) -> None:
        access = self.config.create_physical_access(self.user_1_id, None, None)
        self.config.add_physical_access(self.location_1_id, access)
        location = self.config.get_physical_location(self.location_1_id)
        self.assertIn(access, location.access, "Access was not added to location")
        self.config.remove_physical_access(self.location_1_id, access)
        self.assertNotIn(access, location.access, "Access was not removed from location")

    def test_0012_remove_physical_access_raises_error_for_nonexistent_location(self) -> None:
        access = self.config.create_physical_access(self.user_1_id, None, None)
        nonexistent_location_id = "nonexistent_location"

        with self.assertRaises(ValueError) as context:
            self.config.remove_physical_access(nonexistent_location_id, access)

        self.assertEqual(
            str(context.exception),
            f"Location '{nonexistent_location_id}' does not exist.",
            "Error message does not match expected output for nonexistent location in remove_physical_access"
        )

    def test_00013_add_physical_connection_creates_connection_and_get_physical_connections_returns_it(self) -> None:
        self.config.add_physical_connection(self.location_1_id, self.location_2_id, travel_time)
        connections = self.config.get_physical_connections(self.location_1_id, self.location_2_id)
        self.assertEqual(len(connections), 1, "Physical connection was not added")

    def test_0014_add_physical_connection_raises_error_for_nonexistent_origin(self) -> None:
        nonexistent_origin = "nonexistent_origin"

        with self.assertRaises(ValueError) as context:
            self.config.add_physical_connection(nonexistent_origin, self.location_2_id, travel_time)

        self.assertEqual(
            str(context.exception),
            f"Origin location '{nonexistent_origin}' does not exist.",
            "Error message does not match expected output for nonexistent origin location in add_physical_connection"
        )

    def test_0015_add_physical_connection_raises_error_for_nonexistent_destination(self) -> None:
        nonexistent_destination = "nonexistent_destination"

        with self.assertRaises(ValueError) as context:
            self.config.add_physical_connection(self.location_1_id, nonexistent_destination, travel_time)

        self.assertEqual(
            str(context.exception),
            f"Destination location '{nonexistent_destination}' does not exist.",
            "Error message does not match expected output for nonexistent destination location in add_physical_connection"
        )

    def test_0016_get_physical_connections_returns_correctly_when_destination_is_none(self) -> None:
        self.config.add_physical_connection(self.location_1_id, self.location_2_id, travel_time)
        connections = self.config.get_physical_connections(self.location_1_id, None)
        self.assertEqual(len(connections), 1, "Physical connection was not added")

    def test_0017_get_physical_connections_returns_correctly(self) -> None:
        self.config.add_physical_connection(self.location_1_id, self.location_2_id, travel_time)
        connections = self.config.get_physical_connections(self.location_1_id, self.location_2_id)
        self.assertEqual(len(connections), 1, "Physical connection was not added")

    def test_0018_get_physical_connections_returns_correctly_for_swapped_origin_and_destination(self) -> None:
        self.config.add_physical_connection(self.location_1_id, self.location_2_id, travel_time)

        connections_swapped = self.config.get_physical_connections(self.location_2_id, self.location_1_id)
        self.assertEqual(len(connections_swapped), 1,
                         "Physical connection not found with swapped origin and destination")

    def test_0019_get_physical_connections_raises_error_for_nonexistent_origin(self) -> None:
        nonexistent_origin = "nonexistent_origin"
        destination = self.location_2_id

        with self.assertRaises(ValueError) as context:
            self.config.get_physical_connections(nonexistent_origin, destination)

        self.assertEqual(
            str(context.exception),
            f"Origin location '{nonexistent_origin}' does not exist.",
            "Error message does not match expected output for nonexistent origin in get_physical_connections"
        )

    def test_0020_get_physical_connections_raises_error_for_nonexistent_destination(self) -> None:
        origin = self.location_1_id
        nonexistent_destination = "nonexistent_destination"

        with self.assertRaises(ValueError) as context:
            self.config.get_physical_connections(origin, nonexistent_destination)

        self.assertEqual(
            str(context.exception),
            f"Destination location '{nonexistent_destination}' does not exist.",
            "Error message does not match expected output for nonexistent destination in get_physical_connections"
        )

    def test_0021_remove_physical_connection_removes_connection(self) -> None:
        self.config.add_physical_connection(self.location_1_id, self.location_2_id, travel_time)
        self.config.remove_physical_connection(self.location_1_id, self.location_2_id)
        connections = self.config.get_physical_connections(self.location_1_id, None)
        self.assertEqual(len(connections), 0, "Physical connection was not removed")

    def test_0022_remove_physical_connection_raises_error_for_nonexistent_origin(self) -> None:
        nonexistent_origin = "nonexistent_origin"
        destination = self.location_2_id

        with self.assertRaises(ValueError) as context:
            self.config.remove_physical_connection(nonexistent_origin, destination)

        self.assertEqual(
            str(context.exception),
            f"Origin location '{nonexistent_origin}' does not exist.",
            "Error message does not match expected output for nonexistent origin in remove_physical_connection"
        )

    def test_0023_remove_physical_connection_raises_error_for_nonexistent_destination(self) -> None:
        origin = self.location_1_id
        nonexistent_destination = "nonexistent_destination"

        with self.assertRaises(ValueError) as context:
            self.config.remove_physical_connection(origin, nonexistent_destination)

        self.assertEqual(
            str(context.exception),
            f"Destination location '{nonexistent_destination}' does not exist.",
            "Error message does not match expected output for nonexistent destination in remove_physical_connection"
        )

    def test_0024_place_asset_places_asset_in_location(self) -> None:
        self.config.place_asset(self.location_1_id, self.node_1_id)
        location = self.config.get_physical_location(self.location_1_id)
        self.assertIn(self.node_1_id, location.assets, "Asset was not placed in location")

    def test_0025_place_asset_raises_error_for_nonexistent_location(self) -> None:
        nonexistent_location_id = "nonexistent_location"

        with self.assertRaises(ValueError) as context:
            self.config.place_asset(nonexistent_location_id, self.node_1_id)

        self.assertEqual(
            str(context.exception),
            f"Location '{nonexistent_location_id}' does not exist.",
            "Error message does not match expected output for nonexistent location in place_asset"
        )

    def test_0026_remove_asset_removes_asset_from_location(self) -> None:
        self.config.place_asset(self.location_1_id, self.node_1_id)
        self.config.remove_asset(self.location_1_id, self.node_1_id)
        location = self.config.get_physical_location(self.location_1_id)
        self.assertNotIn(self.node_1_id, location.assets, "Asset was not removed from location")

    def test_0027_remove_asset_raises_error_for_nonexistent_location(self) -> None:
        nonexistent_location_id = "nonexistent_location"

        with self.assertRaises(ValueError) as context:
            self.config.remove_asset(nonexistent_location_id, self.node_1_id)

        self.assertEqual(
            str(context.exception),
            f"Location '{nonexistent_location_id}' does not exist.",
            "Error message does not match expected output for nonexistent location in remove_asset"
        )

    def test_0028_move_asset_moves_asset_between_locations(self) -> None:
        access = self.config.create_physical_access(self.user_1_id, None, None)
        self.config.add_physical_access(self.location_2_id, access)
        self.config.add_physical_connection(self.location_1_id, self.location_2_id, travel_time)
        self.config.place_asset(self.location_1_id, self.user_1_id)
        success, new_location, error = self.config.move_asset(self.location_1_id, self.location_2_id, self.user_1_id)
        self.assertTrue(success, "Failed to move asset between locations")
        self.assertEqual(new_location, self.location_2_id, "Asset was not moved to destination")
        self.assertEqual(error, "", "Unexpected error in asset move")

    def test_0029_move_asset_raises_error_for_nonexistent_origin(self) -> None:
        nonexistent_origin = "nonexistent_origin"
        destination = self.location_2_id

        with self.assertRaises(ValueError) as context:
            self.config.move_asset(nonexistent_origin, destination, self.node_1_id)

        self.assertEqual(
            str(context.exception),
            f"Origin location '{nonexistent_origin}' does not exist.",
            "Error message does not match expected output for nonexistent origin in move_asset"
        )

    def test_0030_move_asset_raises_error_for_nonexistent_destination(self) -> None:
        origin = self.location_1_id
        nonexistent_destination = "nonexistent_destination"

        with self.assertRaises(ValueError) as context:
            self.config.move_asset(origin, nonexistent_destination, self.node_1_id)

        self.assertEqual(
            str(context.exception),
            f"Destination location '{nonexistent_destination}' does not exist.",
            "Error message does not match expected output for nonexistent destination in move_asset"
        )

    def test_0031_move_asset_fails_for_no_connection_between_locations(self) -> None:
        self.config.place_asset(self.location_1_id, self.node_1_id)
        success, new_location, error = self.config.move_asset(self.location_1_id, self.location_2_id, self.node_1_id)

        self.assertFalse(success, "Asset move should have failed due to missing connection")
        self.assertEqual(new_location, self.location_1_id, "Asset location should remain as origin")
        self.assertEqual(error, "No connection between locations",
                         "Error message does not match expected output for missing connection")

    def test_0032_move_asset_fails_when_asset_not_in_origin_location(self) -> None:
        self.config.add_physical_connection(self.location_1_id, self.location_2_id, travel_time)
        success, new_location, error = self.config.move_asset(self.location_1_id, self.location_2_id, self.node_1_id)

        self.assertFalse(success, "Asset move should have failed as asset is not in origin location")
        self.assertEqual(new_location, "", "New location should be empty on failure")
        self.assertEqual(error, "Asset not in origin location",
                         "Error message does not match expected output for missing asset in origin")

    def test_0033_get_assets_returns_assets_for_location(self) -> None:
        self.config.place_asset(self.location_1_id, self.node_1_id)
        assets = self.config.get_assets(self.location_1_id)

        self.assertIn(self.node_1_id, assets, "Asset not found in location assets list")

    def test_0034_get_assets_raises_error_for_nonexistent_location(self) -> None:
        nonexistent_location_id = "nonexistent_location"

        with self.assertRaises(ValueError) as context:
            self.config.get_assets(nonexistent_location_id)

        self.assertEqual(
            str(context.exception),
            f"Location '{nonexistent_location_id}' does not exist.",
            "Error message does not match expected output for nonexistent location in get_assets"
        )

    def test_0035_get_location_returns_correct_location_for_asset(self) -> None:
        self.config.place_asset(self.location_1_id, self.node_1_id)
        location_id = self.config.get_location(self.node_1_id)

        self.assertEqual(location_id, self.location_1_id,
                         "get_location did not return the correct location for the asset")

    def test_0036_get_location_returns_empty_string_for_unassigned_asset(self) -> None:
        location_id = self.config.get_location("unassigned_asset")

        self.assertEqual(location_id, "", "get_location should return an empty string for an unassigned asset")

class TestPhysicalConfiguration(unittest.TestCase):

    def setUp(self) -> None:
        self.env = Environment.create().configure(node_1, node_2, router, *connections_cfg, location_1_cfg, location_2_cfg, physical_connection)
        self.env.control.init()

    def test_0001_physical_configuration_was_set_up_correctly(self) -> None:
        location_1 = self.env.configuration.physical.get_physical_location(location_1_id)
        self.assertEqual(len(location_1.assets), 2, "Location 1 has wrong size of assets array")
        self.assertEqual(len(location_1.access), 0, "Location 1 has wrong size of access array")
        self.assertIn(node_1_id, location_1.assets, "Location 1 does not contain asset node_1_id")
        self.assertIn(router_id, location_1.assets, "Location 1 does not contain asset node_1_id")

        location_2 = self.env.configuration.physical.get_physical_location(location_2_id)
        self.assertEqual(len(location_2.assets), 1, "Location 2 has wrong size of assets array")
        self.assertEqual(len(location_2.access), 0, "Location 2 has wrong size of access array")
        self.assertEqual(location_2.assets[0], node_2_id, "Location 2 does not contain asset node_2_id")

        connections = self.env.configuration.physical.get_physical_connections(location_1_id, location_2_id)
        self.assertEqual(len(connections), 1, "Connections have wrong size")
        self.assertEqual(str(connections[0].travel_time), str(mins(2)), "Connection has wrong travel time")

    def test_0002_move_asset_user_succeeds_when_user_has_access_when_time_is_none(self) -> None:
        self.env.configuration.physical.place_asset(location_1_id, user_1_id)
        user_1_access_to_location_2 = self.env.configuration.physical.create_physical_access(user_1_id, None, None)
        self.env.configuration.physical.add_physical_access(location_2_id, user_1_access_to_location_2)

        success, new_location, error = self.env.configuration.physical.move_asset(location_1_id, location_2_id, user_1_id)
        self.assertTrue(success, "move_asset did not succeed")
        self.assertEqual(new_location, location_2_id,"move_asset did not move the asset to location_2")
        self.assertEqual(error, "","Error is not empty")

    def test_0003_move_asset_user_succeeds_when_user_has_access_when_time_is_in_access_interval(self) -> None:
        self.env.resources.clock._init_time = time_inside_access.timestamp()
        self.env.configuration.physical.place_asset(location_1_id, user_1_id)
        user_1_access_to_location_2 = self.env.configuration.physical.create_physical_access(user_1_id, time_from, time_to)
        self.env.configuration.physical.add_physical_access(location_2_id, user_1_access_to_location_2)

        success, new_location, error = self.env.configuration.physical.move_asset(location_1_id, location_2_id, user_1_id)
        self.assertTrue(success, "move_asset did not succeed")
        self.assertEqual(new_location, location_2_id,"move_asset did not move the asset to location_2")
        self.assertEqual(error, "","Error is not empty")

    def test_0004_move_asset_user_fails_when_user_has_access_when_time_is_out_of_access(self) -> None:
        self.env.resources.clock._init_time = time_out_of_access.timestamp()

        self.env.configuration.physical.place_asset(location_1_id, user_1_id)
        user_1_access_to_location_2 = self.env.configuration.physical.create_physical_access(user_1_id, time_from, time_to)
        self.env.configuration.physical.add_physical_access(location_2_id, user_1_access_to_location_2)

        success, new_location, error = self.env.configuration.physical.move_asset(location_1_id, location_2_id, user_1_id)
        self.assertFalse(success, "move_asset did not fail")
        self.assertEqual(new_location, location_1_id,"move_asset did fail to not move the asset to location_2")
        self.assertEqual(error, "User lacks access rights at the destination.","Error is empty")

    def test_0005_move_asset_node_succeeds_and_does_not_consider_access(self) -> None:
        success, new_location, error = self.env.configuration.physical.move_asset(location_1_id, location_2_id, node_1_id)
        self.assertTrue(success, "move_asset did not succeed")
        self.assertEqual(new_location, location_2_id,"move_asset did not move the asset to location_2")
        self.assertEqual(error, "","Error is not empty")

    def test_0006_move_asset_router_succeeds_and_does_not_consider_access(self) -> None:
        success, new_location, error = self.env.configuration.physical.move_asset(location_1_id, location_2_id, router_id)
        self.assertTrue(success, "move_asset did not succeed")
        self.assertEqual(new_location, location_2_id,"move_asset did not move the asset to location_2")
        self.assertEqual(error, "","Error is not empty")

