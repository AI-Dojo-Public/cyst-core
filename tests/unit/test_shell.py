import unittest

from netaddr import IPAddress, IPNetwork
from cyst.api.configuration.host.service import ActiveServiceConfig
from cyst.api.configuration.network.elements import ConnectionConfig, InterfaceConfig

from cyst.api.configuration.network.firewall import FirewallConfig, FirewallChainConfig
from cyst.api.configuration.network.node import NodeConfig
from cyst.api.configuration.network.router import RouterConfig
from cyst.api.environment.control import EnvironmentState
from cyst.api.environment.environment import Environment
from cyst.api.environment.message import Status, StatusOrigin, StatusValue
from cyst.api.host.service import Service
from cyst.api.logic.access import AccessLevel
from cyst.api.network.firewall import FirewallPolicy, FirewallChainType
from cyst.api.network.node import Node
#from cyst.core.environment.message import MessageImpl
#from cyst.core.network.elements import Endpoint
from cyst_services.forward_shell.main import ForwardShell
from cyst_services.scripted_actor.main import ScriptedActorControl

# Constants for readability
TARGET = "192.168.0.2"
ATTACKER = "192.168.0.3"

SUCCESS = Status(StatusOrigin.SERVICE, StatusValue.SUCCESS)
FAILURE = Status(StatusOrigin.SERVICE, StatusValue.FAILURE)

# Network configuration
target = NodeConfig(
    active_services=[
        ActiveServiceConfig(
            "forward_shell",
            "forward_shell",
            "target",
            AccessLevel.LIMITED,
            id="forward_shell_service",
            configuration=
            {  # to get meaningful response on invalid requests
                "ignore_requests": False,
            })
    ],
    passive_services=[],
    traffic_processors=[],
    shell="",
    interfaces=[InterfaceConfig(IPAddress(TARGET), IPNetwork("192.168.0.2/24"))],
    id="target_node")

attacker = NodeConfig(active_services=[
    ActiveServiceConfig("scripted_actor",
                        "scripted_attacker",
                        "attacker",
                        AccessLevel.LIMITED,
                        id="attacker_service")
],
                      passive_services=[],
                      traffic_processors=[],
                      shell="",
                      interfaces=[InterfaceConfig(IPAddress(ATTACKER), IPNetwork("192.168.0.3/24"))],
                      id="attacker_node")

router = RouterConfig(
    traffic_processors=[
        FirewallConfig(
            default_policy=FirewallPolicy.DENY,
            chains=[
                FirewallChainConfig(
                    type=FirewallChainType.FORWARD,
                    policy=FirewallPolicy.ALLOW,
                    rules=[]
                )
            ]
        )
    ],
    interfaces=[
        InterfaceConfig(IPAddress("192.168.0.1"),
                        IPNetwork("192.168.0.0/24"),
                        index=0),
        InterfaceConfig(IPAddress("192.168.0.1"),
                        IPNetwork("192.168.0.0/24"),
                        index=1),
      ],
    id="router"
)

connections = [
    ConnectionConfig("target_node", 0, "router", 0),
    ConnectionConfig("attacker_node", 0, "router", 1),
]


class TestForwardShell(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.env = Environment.create().configure(target, attacker, router, *connections)
        cls.env.control.init()
        cls.env.control.add_pause_on_response("attacker_node.scripted_attacker")

        cls.attacker = cls.env.configuration.service.get_service_interface(
            cls.env.configuration.general.get_object_by_id("attacker_node.scripted_attacker",
                                                           Service).active_service,
            ScriptedActorControl)

        cls.shell = cls.env.configuration.service.get_service_interface(
            cls.env.configuration.general.get_object_by_id("target_node.forward_shell",
                                                           Service).active_service, ForwardShell)

        cls.node = cls.env.configuration.general.get_object_by_id("target_node", Node)

        cls.actions = {a.id: a for a in cls.env.resources.action_store.get_prefixed("cyst")}

    def test_0000_init(self) -> None:
        self.assertEqual(self.env.control.state, EnvironmentState.INIT,
                         "Environment not instantiated")
        self.assertNotIn(None, [self.attacker, self.node], "Environment not configured properly")

    def test_0001_send_action(self) -> None:
        open_session = self.actions["cyst:active_service:open_session"]

        self.attacker.execute_action(TARGET, "forward_shell", open_session)
        self.env.control.run()
        response = self.attacker.get_last_response()

        self.assertEqual(response.status, SUCCESS, "Action did not succeed")
        self.assertIsNotNone(response.session, "Session was not received")
        self.assertTupleEqual(response.session.start, (IPAddress(ATTACKER), "scripted_attacker"),
                              "Session should start at the attacker service")
        self.assertTupleEqual(response.session.end, (IPAddress(TARGET), "forward_shell"),
                              "Session should end at the forward shell")

    def test_0002_invalid_action(self) -> None:
        invalid_action = self.actions["cyst:active_service:action_1"]

        self.attacker.execute_action(TARGET, "forward_shell", invalid_action)
        self.env.control.run()
        response = self.attacker.get_last_response()

        self.assertEqual(response.status, FAILURE, "Invalid action executed successfully")

    @unittest.skip("find out how to send dummy response")
    def test_0003_send_response(self) -> None:
        # create dummy request and point its origin to attacker
        request = self.env.messaging.create_request(ATTACKER, "active_service")
        if isinstance(request, MessageImpl):
            request.set_origin(Endpoint("foo", 0, IPAddress(TARGET)))
            request.set_src_ip(IPAddress(TARGET))
        response = self.env.messaging.create_response(request, SUCCESS)

        self.env.messaging.send_message(response)
        ok, _ = self.env.control.run()

        self.assertTrue(ok, "Response was successful")


class TestReverseShell(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.env = Environment.create().configure(target, attacker, router, *connections)
        cls.env.control.init()
        cls.env.control.add_pause_on_response("attacker_node.scripted_attacker")
        cls.env.control.add_pause_on_response("target_node.reverse_shell")

        cls.attacker = cls.env.configuration.service.get_service_interface(
            cls.env.configuration.general.get_object_by_id("attacker_node.scripted_attacker",
                                                           Service).active_service,
            ScriptedActorControl)
        cls.node = cls.env.configuration.general.get_object_by_id("target_node", Node)

        cls.actions = {a.id: a for a in cls.env.resources.action_store.get_prefixed("cyst")}

        # dummy request from which a response will be formed
        request = cls.env.messaging.create_request(TARGET, "scripted_attacker",
                                                   cls.actions["cyst:active_service:action_1"])

        configuration = {
            "ignore_requests": False,
            "target": (IPAddress(ATTACKER), "scripted_attacker"),
            "delay": 30,  # not useful in this synthetic test
            "origin": request
        }

        shell = cls.env.configuration.service.create_active_service("reverse_shell",
                                                                    "attacker",
                                                                    "reverse_shell",
                                                                    cls.node,
                                                                    configuration=configuration)

        assert shell is not None
        cls.reverse_shell = shell

    def test_0000_init(self) -> None:
        self.assertEqual(self.env.control.state, EnvironmentState.INIT,
                         "Environment not instantiated")
        self.assertNotIn(None, [self.attacker, self.node, self.reverse_shell],
                         "Environment not configured properly")

    def test_0001_spawn_reverse_shell(self) -> None:
        self.env.configuration.node.add_service(self.node, self.reverse_shell)

        self.assertIn("reverse_shell", self.node.services,
                      "Reverse shell is not part of node's services")

    def test_0002_receive_open_shell_action(self) -> None:
        self.env.configuration.node.add_service(self.node, self.reverse_shell)

        self.env.control.run()
        request = self.attacker.get_last_request()

        self.assertIsNotNone(request, "No request received")
        self.assertIsNotNone(request.action, "Request does not contain any action")
        self.assertEqual(request.action.id, "cyst:active_service:open_session",
                         "Got incorrect action")

    def test_0003_open_session_from_request(self) -> None:
        self.env.configuration.node.add_service(self.node, self.reverse_shell)

        self.env.control.run()
        request = self.attacker.get_last_request()
        session = self.env.messaging.open_session(request)

        self.assertIsNotNone(session, "Session was not received")
        self.assertTupleEqual(session.start, (IPAddress(TARGET), "reverse_shell"),
                              "Session should start at the reverse shell")
        self.assertTupleEqual(session.end, (IPAddress(ATTACKER), "scripted_attacker"),
                              "Session should end at the attacker service")

    def test_0004_invalid_configuration_no_target(self) -> None:
        with (self.assertRaises(Exception)):
            bad_shell = self.env.configuration.service.create_active_service(
                "_reverse_shell", "attacker", "reverse_shell", self.node)
            self.env.configuration.node.add_service(self.node, bad_shell)
