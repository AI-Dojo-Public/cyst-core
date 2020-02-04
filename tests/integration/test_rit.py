import unittest
import uuid

from environment.access import Authorization, AccessLevel, Policy
from environment.action import ActionList
from environment.environment import Environment, EnvironmentState, EnvironmentProxy, PassiveNode
from environment.exploit import Exploit, ExploitLocality, ExploitCategory, VulnerableService, ExploitParameter, ExploitParameterType
from environment.exploit_store import ExploitStore
from environment.message import StatusValue, StatusOrigin
from environment.network import Switch
from environment.network_elements import Endpoint
from environment.node import Service, NodeView
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
        node_root = Authorization("root", ["target1"], None, AccessLevel.ELEVATED, uuid.uuid4())
        Policy().add_authorization(node_root)

        # SSH service, with valid authentication grants a user access to the system
        ssh_service = Service("openssh", "8.1.0")
        # SSH enables session creation
        ssh_service.set_enable_session(True)
        # Sessions can be opened by ordinary users and root
        ssh_service.set_session_access_level(AccessLevel.LIMITED)
        # Successful exploit of the service grants attacker a root level access to the system
        ssh_service.set_service_access_level(AccessLevel.ELEVATED)
        # make the ssh authorization available to the attacker
        cls._ssh_auth1 = Authorization("user1", ["target1"], ["openssh"], AccessLevel.LIMITED, uuid.uuid4())
        ssh_auth2 = Authorization("user2", ["target1"], ["openssh"], AccessLevel.LIMITED, uuid.uuid4())
        Policy().add_authorization(cls._ssh_auth1, ssh_auth2)

        # Bash service, accessible only locally
        bash_service = Service("bash", "5.0.0", local=True)
        # TODO Bash and other services should probably support local code execution exploits
        bash_service.set_service_access_level(AccessLevel.LIMITED)
        bash_auth1 = Authorization("user1", ["target1"], ["bash"], AccessLevel.LIMITED, uuid.uuid4())
        bash_auth2 = Authorization("user2", ["target1"], ["bash"], AccessLevel.LIMITED, uuid.uuid4())
        Policy().add_authorization(bash_auth1, bash_auth2)

        # Setting bash as a shell - this way, any successful code-execution exploits to other services will also be
        # given an access to the bash authorizations
        target.set_shell(bash_service)

        # HTTP service provides a list of users when queried for information. May get system access with exploit
        # Authorizations only added as a public data and are not registered in the policy, because on their own, they do not
        # grant any access.
        http_service = Service("lighttpd", "1.4.54")
        http_auth1 = Authorization("user1", ["target1"])
        http_auth2 = Authorization("user2", ["target1"])
        http_service.add_public_authorization(http_auth1, http_auth2)

        # Successful exploit gives user a limited access to the system
        http_service.set_service_access_level(AccessLevel.LIMITED)

        # Add system exploitability
        exploit1 = Exploit("http_exploit", [VulnerableService("lighttpd", "1.4.54")], ExploitLocality.REMOTE, ExploitCategory.CODE_EXECUTION)
        exploit2 = Exploit("ftp_exploit", [VulnerableService("vsftpd", "3.0.3")], ExploitLocality.REMOTE, ExploitCategory.CODE_EXECUTION)
        exploit3 = Exploit("bash_user_exploit", [VulnerableService("bash", "5.0.0")], ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION, ExploitParameter(ExploitParameterType.IDENTITY))
        ExploitStore().add_exploit(exploit1, exploit2, exploit3)

        target.add_service(ssh_service)
        target.add_service(http_service)
        target.add_service(bash_service)

        # Place a switch in front of the target
        switch = Switch("switch1", cls._env)
        switch.add_port("192.168.0.1", "255.255.255.0")

        # Create an attacker
        proxy = EnvironmentProxy(cls._env, "attacker1")
        cls._attacker = SimpleAttacker("attacker1", env=proxy)

        # Connect the environment pieces
        cls._env.add_node(target)
        cls._env.add_node(switch)
        cls._env.add_node(cls._attacker)

        # TODO change this to env method, once this is merged from bronze_butler branch
        switch.connect_node(target, net="192.168.0.0/24")
        switch.connect_node(cls._attacker, net="192.168.0.0/24")

    # Test correct handling of active scans, namely:
    # - successful scanning of a live machine
    # - unsuccessful scanning of non-existing machine
    # - scanning of an un-routable target
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

    # Test correct gathering of running services
    def test_0001_active_recon_service_scan(self) -> None:

        action = self._actions["rit:active_recon:service_discovery"]
        self._attacker.execute_action("192.168.0.2", "", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "Services disclosed")
        self.assertEqual(message.content, ["openssh", "lighttpd", "bash"])

    # Test getting correct versions of services running on the target and an attempt to get a version of a
    # service, which is not running
    def test_0002_active_recon_vulnerability_discovery(self) -> None:

        action = self._actions["rit:active_recon:vulnerability_discovery"]
        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "Potential vulnerabilities disclosed")
        self.assertEqual(message.content, ["lighttpd-1.4.54"])

        self._attacker.execute_action("192.168.0.2", "nonexisting_service", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Vulnerability of non-existent service not disclosed")

    # Test extraction of publicly available information from the http service
    def test_0003_active_recon_information_discovery(self) -> None:

        action = self._actions["rit:active_recon:information_discovery"]
        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "Information disclosed")

        authorizations = message.content
        for index, auth in enumerate(authorizations):
            self.assertEqual(auth, Authorization("user" + str(index + 1), ["target1"]))

    def test_0004_ensure_access_command_and_control(self) -> None:

        action = self._actions["rit:ensure_access:command_and_control"]

        # Three variations of the c&c action - with authorization, with exploit (with or without wrong authorization)
        #                                      and without anything + some errors because of omissions
        self._attacker.execute_action("192.168.0.2", "", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because service not specified")

        self._attacker.execute_action("192.168.0.2", "nonexistent_service", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because wrong service specified")

        self._attacker.execute_action("192.168.0.2", "openssh", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because neither auth nor exploit were provided")

        self._attacker.execute_action("192.168.0.2", "openssh", action, authorization=self._ssh_auth1)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "Correctly established a session")
        self.assertTrue(isinstance(message.content, NodeView), "Got a node view of the target")
        self.assertEqual(message.session.endpoint, Endpoint("target1", 0))

        # Create dud authorization, that fails because of wrong access token
        ssh_auth = Authorization("user2", ["target1"], ["ssh"], AccessLevel.LIMITED, uuid.uuid4())
        good_exploit = ExploitStore().get_exploit(service="lighttpd", category=ExploitCategory.CODE_EXECUTION)[0]
        action.set_exploit(good_exploit)

        self._attacker.execute_action("192.168.0.2", "lighttpd", action, authorization=ssh_auth)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "Correctly established a session")
        self.assertTrue(isinstance(message.content, NodeView), "Got a node view of the target")
        self.assertEqual(message.session.endpoint, Endpoint("target1", 0))
        self.assertEqual(message.authorization.identity, "lighttpd", "Got correct identity for newly created authorization")

        # Bad exploit used
        bad_exploit = ExploitStore().get_exploit(service="vsftpd")[0]
        action.set_exploit(bad_exploit)

        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.FAILURE, "Wrong exploit used")

    def test_0005_privilege_escalation_user_privilege_escalation(self) -> None:

        cc_action = self._actions["rit:ensure_access:command_and_control"]
        # Clear old data from the previous test
        cc_action.set_exploit(None)
        cc_exploit = ExploitStore().get_exploit(service="lighttpd", category=ExploitCategory.CODE_EXECUTION)[0]

        # TODO With this, all auth manipulation exploits can be interchangeably used for user and root priv escalation
        # This should probably be done otherwise
        user_action = self._actions["rit:privilege_escalation:user_privilege_escalation"]
        user_exploit = ExploitStore().get_exploit(service="bash", category=ExploitCategory.AUTH_MANIPULATION)[0]

        # The correct order of actions is:
        # - using an lighttpd exploit gain session with access under the lighttpd user
        # - using a bash exploit switch to a another system user

        # --------------------------------------------------------------------------------------------------------------
        # Sanity tests (round 1)
        # --------------------------------------------------------------------------------------------------------------
        self._attacker.execute_action("192.168.0.2", "", user_action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because service not specified")

        self._attacker.execute_action("192.168.0.2", "nonexistent_service", user_action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.NODE, "Got response from the node")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because wrong service specified")

        # --------------------------------------------------------------------------------------------------------------
        # Establish a session using the C&C action with the lighttpd exploit
        # --------------------------------------------------------------------------------------------------------------
        cc_action.set_exploit(cc_exploit)
        self._attacker.execute_action("192.168.0.2", "lighttpd", cc_action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        session = message.session
        auth = message.authorization

        self.assertEqual(session.endpoint.id, "target1", "Got correct session")
        self.assertEqual(auth.services, ["lighttpd", "bash"], "Got correct authentication")

        # --------------------------------------------------------------------------------------------------------------
        # Sanity tests (round 2)
        # --------------------------------------------------------------------------------------------------------------
        intentionally_remote_exploit = ExploitStore().get_exploit(service="lighttpd", category=ExploitCategory.CODE_EXECUTION)[0]
        user_action.set_exploit(intentionally_remote_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        # Result and state are discarded from now on
        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because non-local exploit used")

        # --------------------------------------------------------------------------------------------------------------
        # Don't try this at home
        user_action.set_exploit(Exploit("dummy_local_exploit", None, locality=ExploitLocality.LOCAL, category=ExploitCategory.DATA_MANIPULATION))
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because exploit of wrong category used")

        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(Exploit("too_many_param_local_exploit", None, ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION,
                                        ExploitParameter(ExploitParameterType.NONE), ExploitParameter(ExploitParameterType.NONE)))
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because exploit uses two parameters")

        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(Exploit("wrong_param_local_exploit", None, ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION,
                                ExploitParameter(ExploitParameterType.NONE)))
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because exploit uses wrong parameter type")

        # --------------------------------------------------------------------------------------------------------------
        user_exploit.parameters[0].set_value("user1")
        user_action.set_exploit(user_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because no session specified")

        # --------------------------------------------------------------------------------------------------------------
        self._attacker.execute_action("192.168.0.2", "openssh", user_action, session, auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.ERROR, "Failed because wrong authentication specified")

        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(Exploit("old_bash_user_exploit", [VulnerableService("bash", "3.0.0")], ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION, ExploitParameter(ExploitParameterType.IDENTITY)))
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from the service")
        self.assertEqual(message.status.value, StatusValue.FAILURE, "Failed because of unusable exploit")

        # --------------------------------------------------------------------------------------------------------------
        user_exploit.parameters[0].set_value("user3")
        user_action.set_exploit(user_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from service")
        self.assertEqual(message.status.value, StatusValue.FAILURE, "Failed because of unavailable user")

        # --------------------------------------------------------------------------------------------------------------
        # Successful exploit
        # --------------------------------------------------------------------------------------------------------------
        user_exploit.parameters[0].set_value("user1")
        user_action.set_exploit(user_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status.origin, StatusOrigin.SERVICE, "Got response from service")
        self.assertEqual(message.status.value, StatusValue.SUCCESS, "We correctly commenced the exploit")
        self.assertEqual(message.authorization.identity, "user1", "Got authorization for requested user")


if __name__ == '__main__':
    unittest.main()
