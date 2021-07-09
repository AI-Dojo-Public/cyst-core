import unittest

from netaddr import IPAddress

from cyst.api.logic.access import AccessLevel
from cyst.api.environment.environment import Environment
from cyst.api.environment.control import EnvironmentState
from cyst.api.environment.configuration import ServiceParameter
from cyst.api.environment.message import StatusOrigin, StatusValue, Status
from cyst.api.network.node import Node
from cyst.api.network.session import Session

from cyst.services.scripted_attacker.main import ScriptedAttackerControl


class TestMETAIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._env = Environment.create()
        cls._env.control.init()

        cls._action_list = cls._env.resources.action_store.get_prefixed("meta")
        cls._actions = {}
        for action in cls._action_list:
            cls._actions[action.id] = action

        # Many META action are tied to other action for effects, so we have to use meta and something
        cls._action_list = cls._env.resources.action_store.get_prefixed("aif")
        for action in cls._action_list:
            cls._actions[action.id] = action

        # Function aliases
        create_node = cls._env.configuration.node.create_node
        create_router = cls._env.configuration.node.create_router
        create_active_service = cls._env.configuration.service.create_active_service
        create_passive_service = cls._env.configuration.service.create_passive_service
        add_service = cls._env.configuration.node.add_service
        set_service_parameter = cls._env.configuration.service.set_service_parameter
        create_interface = cls._env.configuration.node.create_interface
        add_node = cls._env.configuration.network.add_node
        add_connection = cls._env.configuration.network.add_connection
        add_interface = cls._env.configuration.node.add_interface
        get_service_interface = cls._env.configuration.service.get_service_interface

        # Create a target
        cls._target = create_node("target1")
        cls._all_auth = cls._env.policy.create_authorization("root", ["target1"], ["*"], AccessLevel.ELEVATED)
        cls._env.policy.add_authorization(cls._all_auth)

        ssh_service = create_passive_service("openssh", owner="ssh", version="8.1.0", service_access_level=AccessLevel.ELEVATED)
        set_service_parameter(ssh_service.passive_service, ServiceParameter.ENABLE_SESSION, True)
        set_service_parameter(ssh_service.passive_service, ServiceParameter.SESSION_ACCESS_LEVEL, AccessLevel.LIMITED)

        add_service(cls._target, ssh_service)

        # Create an attacker
        attacker_node = create_node("attacker_node")
        attacker_service = create_active_service("scripted_attacker", "attacker", "scripted_attacker", attacker_node)
        add_service(attacker_node, attacker_service)
        cls._attacker: ScriptedAttackerControl = get_service_interface(attacker_service.active_service, ScriptedAttackerControl)

        # Place a router between target and attacker
        cls._router = create_router("router1", cls._env.messaging)
        add_interface(cls._router, create_interface("192.168.0.1", "255.255.255.0"))

        # Connect the attacker and the target to the router
        add_connection(attacker_node, cls._router, net="192.168.0.1/24")
        add_connection(cls._target, cls._router, net="192.168.0.1/24")

        # Add all nodes to the environment
        add_node(attacker_node)
        add_node(cls._target)
        add_node(cls._router)

        cls._env.control.add_pause_on_response("attacker_node.scripted_attacker")

    def test_0000_inspect_node(self) -> None:
        # Connect the attacker to the target
        action = self._actions["aif:ensure_access:command_and_control"]
        target = self._target.interfaces[0].ip

        self._attacker.execute_action(str(target), "openssh", action, auth=self._all_auth)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Acction was successful")
        self.assertTrue(message.session and isinstance(message.session, Session), "Received a session back")

        session = message.session
        action = self._actions["meta:inspect:node"]

        self._attacker.execute_action(str(target), "", action, session=session)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.SUCCESS), "Acction was successful")
        self.assertTrue(message.content and isinstance(message.content, Node), "Received a node back")

        node: Node = message.content
        self.assertEqual(IPAddress("192.168.0.3"), node.interfaces[0].ip, "Got correct IP address back")
