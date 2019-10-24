import unittest
import uuid

from environment.access import Authorization, AccessLevel, Policy
from environment.action import ActionList
from environment.environment import Environment, EnvironmentState, PassiveNode
from environment.message import StatusValue, StatusOrigin
from environment.network import Switch
from environment.node import Service, Node
from attackers.simple import SimpleAttacker


class TestRITIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._env = Environment(pause_on_response=["attacker1"])

        cls._action_list = ActionList().get_actions("rit")
        cls._actions = {}
        for action in cls._action_list:
            cls._actions[action.tags[0].name] = action

        Policy().reset()

        # A passive node that:
        # - is running two services - ssh and a http
        # - has two users and a root
        # - contains interesting data data can be shared
        target = PassiveNode("target1")
        node_root = Authorization("root", ["node1"], None, AccessLevel.ELEVATED, uuid.uuid4())
        Policy().add_authorization(node_root)

        # SSH service, with valid authentication grants a user access to the system
        ssh_service = Service("ssh")
        ssh_service.add_tags("openssh-8.1")
        ssh_auth1 = Authorization("user1", ["node1"], ["ssh"], AccessLevel.LIMITED, uuid.uuid4())
        ssh_auth2 = Authorization("user2", ["node1"], ["ssh"], AccessLevel.LIMITED, uuid.uuid4())
        Policy().add_authorization(ssh_auth1, ssh_auth2)

        # HTTP service provides a list of users when queried for information. May get system access with exploit
        # Authorizations only added as a public data and are not registered in the policy, because on their own, they do not
        # grant any access.
        http_service = Service("http")
        http_service.add_tags("lighttpd-1.4.54")
        http_auth1 = Authorization("user1", ["node1"])
        http_auth2 = Authorization("user2", ["node1"])
        http_service.add_public_authorization(http_auth1, http_auth2)

        target.add_service(ssh_service)
        target.add_service(http_service)

        # Place a switch in front of the target
        switch = Switch("switch1", "192.168.0.1", "255.255.255.0", cls._env)

        # Create an attacker
        cls._attacker = SimpleAttacker("attacker1", env=cls._env)

        # Connect the environment pieces
        cls._env.add_node(target)
        cls._env.add_node(switch)
        cls._env.add_node(cls._attacker)

        cls._env.add_connection(target, switch)
        cls._env.add_connection(switch, cls._attacker)

    def test_0000_active_recon_host_scan(self) -> None:

        action = self._actions["rit:active_recon:host_discovery"]
        self._attacker.execute_action("192.168.0.2", "", action)

        result, state = self._env.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "Liveliness confirmed")

        self._attacker.execute_action("192.168.0.6", "", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NETWORK, "Got response from the network")
        self.assertEqual(message.status.value, StatusValue.FAILURE, "Host unreachable")

        self._attacker.execute_action("192.168.1.6", "", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NETWORK, "Got response from the network")
        self.assertEqual(message.status.value, StatusValue.FAILURE, "Host un-routable")

    def test_0001_active_recon_service_scan(self) -> None:

        action = self._actions["rit:active_recon:service_discovery"]
        self._attacker.execute_action("192.168.0.2", "", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "Services disclosed")
        self.assertEqual(message.content, ["ssh", "http"])

    def test_0002_active_recon_vulnerability_discovery(self) -> None:

        action = self._actions["rit:active_recon:vulnerability_discovery"]
        self._attacker.execute_action("192.168.0.2", "http", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "Vulnerability disclosed")
        self.assertEqual(message.content, ["lighttpd-1.4.54"])

        self._attacker.execute_action("192.168.0.2", "nonexisting_service", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Vulnerability of non-existent service not disclosed")

    def test_0003_active_recon_information_discovery(self) -> None:

        action = self._actions["rit:active_recon:information_discovery"]
        self._attacker.execute_action("192.168.0.2", "http", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "Information disclosed")

        authorizations = message.content
        for index, auth in enumerate(authorizations):
            self.assertEqual(auth, Authorization("user" + str(index + 1), ["node1"]))


if __name__ == '__main__':
    unittest.main()
