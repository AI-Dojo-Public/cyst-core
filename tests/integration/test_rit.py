import unittest
import uuid

from environment.access import Authorization, AccessLevel, Policy
from environment.action import ActionList
from environment.environment import Environment, EnvironmentState, EnvironmentProxy, PassiveNode
from environment.exploit import Exploit, ExploitLocality, ExploitCategory, VulnerableService, ExploitParameter, ExploitParameterType
from environment.exploit_store import ExploitStore
from environment.message import StatusValue, StatusOrigin, Status
from environment.network import Router
from environment.network_elements import Endpoint
from environment.node import Service, NodeView, Data
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

        bash_service.add_public_data(Data(None, "user1", "Worthless data"))
        bash_service.add_private_data(Data(None, "user1", "Interesting data, somehow hidden in bash"))

        # HTTP service provides a list of users when queried for information. May get system access with exploit
        # Authorizations only added as a public data and are not registered in the policy, because on their own, they do not
        # grant any access.
        http_service = Service("lighttpd", "1.4.54")
        http_auth1 = Authorization("user1", ["target1"])
        http_auth2 = Authorization("user2", ["target1"])
        http_service.add_public_authorization(http_auth1, http_auth2)

        # Successful exploit gives user a limited access to the system
        http_service.set_service_access_level(AccessLevel.LIMITED)

        # Add some public and private data to the service
        http_service.add_public_data(Data(None, "user1", "Completely useless data"))
        http_service.add_public_data(Data(None, "user1", "Another batch of useless data"))
        http_service.add_private_data(Data(None, "user2", "Much more interesting piece of information"))

        # Add system exploitability
        exploit1 = Exploit("http_exploit", [VulnerableService("lighttpd", "1.4.54")], ExploitLocality.REMOTE, ExploitCategory.CODE_EXECUTION)
        exploit2 = Exploit("ftp_exploit", [VulnerableService("vsftpd", "3.0.3")], ExploitLocality.REMOTE, ExploitCategory.CODE_EXECUTION)
        exploit3 = Exploit("bash_user_exploit", [VulnerableService("bash", "5.0.0")], ExploitLocality.LOCAL,
                           ExploitCategory.AUTH_MANIPULATION, ExploitParameter(ExploitParameterType.IDENTITY),
                           ExploitParameter(ExploitParameterType.ENABLE_ELEVATED_ACCESS, "FALSE", immutable=True))
        exploit4 = Exploit("bash_root_exploit", [VulnerableService("bash", "5.0.0")], ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION,
                           ExploitParameter(ExploitParameterType.ENABLE_ELEVATED_ACCESS, "TRUE", immutable=True))
        exploit5 = Exploit("bash_master_exploit", [VulnerableService("bash", "5.0.0")], ExploitLocality.LOCAL,
                           ExploitCategory.AUTH_MANIPULATION,
                           ExploitParameter(ExploitParameterType.ENABLE_ELEVATED_ACCESS, "TRUE", immutable=True),
                           ExploitParameter(ExploitParameterType.IMPACT_IDENTITY, "ALL", immutable=True),
                           ExploitParameter(ExploitParameterType.IMPACT_NODE, "ALL", immutable=True),
                           ExploitParameter(ExploitParameterType.IMPACT_SERVICE, "ALL", immutable=True))

        ExploitStore().add_exploit(exploit1, exploit2, exploit3, exploit4, exploit5)

        target.add_service(ssh_service)
        target.add_service(http_service)
        target.add_service(bash_service)

        # Place a router in front of the target
        router = Router("router1", cls._env)
        router.add_port("192.168.0.1", "255.255.255.0")

        # Create an attacker
        proxy = EnvironmentProxy(cls._env, "attacker1")
        cls._attacker = SimpleAttacker("attacker1", env=proxy)

        # Connect the environment pieces
        cls._env.add_node(target)
        cls._env.add_node(router)
        cls._env.add_node(cls._attacker)

        # TODO change this to env method, once this is merged from bronze_butler branch
        cls._env.add_connection(router, target, net="192.168.0.0/24")
        cls._env.add_connection(router, cls._attacker, net="192.168.0.0/24")

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
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.SUCCESS), "Liveliness confirmed")

        self._attacker.execute_action("192.168.0.6", "", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NETWORK, StatusValue.FAILURE), "Host unreachable")

        self._attacker.execute_action("192.168.1.6", "", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NETWORK, StatusValue.FAILURE), "Host un-routable")

    # Test correct gathering of running services
    def test_0001_active_recon_service_scan(self) -> None:

        action = self._actions["rit:active_recon:service_discovery"]
        self._attacker.execute_action("192.168.0.2", "", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.SUCCESS), "Services disclosed")
        self.assertEqual(message.content, ["openssh", "lighttpd", "bash"])

    # Test getting correct versions of services running on the target and an attempt to get a version of a
    # service, which is not running
    def test_0002_active_recon_vulnerability_discovery(self) -> None:

        action = self._actions["rit:active_recon:vulnerability_discovery"]
        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Potential vulnerabilities disclosed")
        self.assertEqual(message.content, ["lighttpd-1.4.54"])

        self._attacker.execute_action("192.168.0.2", "nonexisting_service", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Vulnerability of non-existent service not disclosed")

    # Test extraction of publicly available information from the http service
    def test_0003_active_recon_information_discovery(self) -> None:

        action = self._actions["rit:active_recon:information_discovery"]
        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Information disclosed")

        counter = 0
        authorizations = message.content
        for auth in authorizations:
            # The service contains public data as well
            if type(auth) is Authorization:
                self.assertEqual(auth, Authorization("user" + str(counter + 1), ["target1"]))
                counter += 1

    def test_0004_ensure_access_command_and_control(self) -> None:

        action = self._actions["rit:ensure_access:command_and_control"]

        # Three variations of the c&c action - with authorization, with exploit (with or without wrong authorization)
        #                                      and without anything + some errors because of omissions
        self._attacker.execute_action("192.168.0.2", "", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because service not specified")

        self._attacker.execute_action("192.168.0.2", "nonexistent_service", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because wrong service specified")

        self._attacker.execute_action("192.168.0.2", "openssh", action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because neither auth nor exploit were provided")

        self._attacker.execute_action("192.168.0.2", "openssh", action, authorization=self._ssh_auth1)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Correctly established a session")
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
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Correctly established a session")
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
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), "Wrong exploit used")

    def test_0005_privilege_escalation_user_and_root_privilege_escalation(self) -> None:

        cc_action = self._actions["rit:ensure_access:command_and_control"]
        # Clear old data from the previous test
        cc_action.set_exploit(None)
        cc_exploit = ExploitStore().get_exploit(service="lighttpd", category=ExploitCategory.CODE_EXECUTION)[0]

        # TODO With this, all auth manipulation exploits can be interchangeably used for user and root priv escalation
        # This should probably be done otherwise
        user_action = self._actions["rit:privilege_escalation:user_privilege_escalation"]
        user_exploit = None

        root_action = self._actions["rit:privilege_escalation:root_privilege_escalation"]
        root_exploit = None

        master_exploit = None

        auth_exploits = ExploitStore().get_exploit(service="bash", category=ExploitCategory.AUTH_MANIPULATION)
        for exploit in auth_exploits:
            ea = exploit.parameters.get(ExploitParameterType.ENABLE_ELEVATED_ACCESS, None)
            ii = exploit.parameters.get(ExploitParameterType.IDENTITY, None)
            sr = exploit.parameters.get(ExploitParameterType.IMPACT_SERVICE, None)

            if sr:
                master_exploit = exploit
            elif ea and ea.value == "TRUE":
                root_exploit = exploit
            elif ii:
                user_exploit = exploit

        # The correct order of actions is:
        # - using an lighttpd exploit gain session with access under the lighttpd user
        # - using a bash exploit switch to a another system user

        # --------------------------------------------------------------------------------------------------------------
        # Sanity tests (round 1)
        # --------------------------------------------------------------------------------------------------------------
        self._attacker.execute_action("192.168.0.2", "", user_action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because service not specified")

        self._attacker.execute_action("192.168.0.2", "nonexistent_service", user_action)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because wrong service specified")

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

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because non-local exploit used")

        # --------------------------------------------------------------------------------------------------------------
        # Don't try this at home
        user_action.set_exploit(Exploit("dummy_local_exploit", None, locality=ExploitLocality.LOCAL, category=ExploitCategory.DATA_MANIPULATION))
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because exploit of wrong category used")

        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(Exploit("too_many_param_local_exploit", None, ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION,
                                        ExploitParameter(ExploitParameterType.NONE), ExploitParameter(ExploitParameterType.NONE)))
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because exploit uses two parameters")

        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(Exploit("wrong_param_local_exploit", None, ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION,
                                ExploitParameter(ExploitParameterType.NONE)))
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because exploit uses wrong parameter type")

        # --------------------------------------------------------------------------------------------------------------
        user_exploit.parameters[ExploitParameterType.IDENTITY].set_value("user1")
        user_action.set_exploit(user_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because no session specified")

        # --------------------------------------------------------------------------------------------------------------
        self._attacker.execute_action("192.168.0.2", "openssh", user_action, session, auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because wrong authentication specified")

        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(Exploit("old_bash_user_exploit", [VulnerableService("bash", "3.0.0")], ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION, ExploitParameter(ExploitParameterType.IDENTITY)))
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), "Failed because of unusable exploit")

        # --------------------------------------------------------------------------------------------------------------
        user_exploit.parameters[ExploitParameterType.IDENTITY].set_value("user3")
        user_action.set_exploit(user_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        result, state = self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), "Failed because of unavailable user")

        # --------------------------------------------------------------------------------------------------------------
        # Successful user exploit
        # --------------------------------------------------------------------------------------------------------------
        user_exploit.parameters[ExploitParameterType.IDENTITY].set_value("user1")
        user_action.set_exploit(user_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "We correctly commenced the exploit")
        self.assertEqual(message.authorization.identity, "user1", "Got authorization for requested user")

        # --------------------------------------------------------------------------------------------------------------
        # Successful root exploit
        # --------------------------------------------------------------------------------------------------------------
        root_action.set_exploit(root_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", root_action, session, auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "We correctly commenced the exploit")
        self.assertEqual(message.authorization.identity, "root", "Got authorization for root")
        self.assertEqual(message.authorization.access_level, AccessLevel.ELEVATED, "Got elevated access level")

        # --------------------------------------------------------------------------------------------------------------
        # Test master exploit
        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(master_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "We correctly commenced the exploit")
        self.assertEqual(message.authorization.identity, "*", "Got authorization for anyone")
        self.assertEqual(message.authorization.nodes, ["*"], "Got authorization for anyone")
        self.assertEqual(message.authorization.services, ["*"], "Got authorization for anyone")
        self.assertEqual(message.authorization.access_level, AccessLevel.LIMITED, "Got elevated access level")

    def test_0006_disclosure_data_exfiltration(self) -> None:

        action = self._actions["rit:disclosure:data_exfiltration"]

        # --------------------------------------------------------------------------------------------------------------
        # Sanity tests
        # --------------------------------------------------------------------------------------------------------------
        self._attacker.execute_action("192.168.0.2", "", action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because service not specified")

        self._attacker.execute_action("192.168.0.2", "nonexistent_service", action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because wrong service specified")

        self._attacker.execute_action("192.168.0.2", "bash", action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because local service specified")

        # --------------------------------------------------------------------------------------------------------------
        # Disclose publicly available data
        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Got public data from lighttpd service")
        self.assertTrue(type(message.content) is list and len(message.content) == 2 and message.content[0].owner == "user1", "Got correct data")

        # Exploit httpd to get access
        remote_exploit = ExploitStore().get_exploit(service="lighttpd")[0]
        cc_action = self._actions["rit:ensure_access:command_and_control"]
        cc_action.set_exploit(remote_exploit)

        self._attacker.execute_action("192.168.0.2", "lighttpd", cc_action)

        self._env.resume()
        message = self._attacker.get_last_response()

        session = message.session
        auth = message.authorization

        # At this point, we can guess which users are present on the system from message.content, which is a NodeView.
        # TODO However, there is no clear mapping of service -> user accounts

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Established a session")
        self.assertTrue("lighttpd" in auth.services, "Exploited lighttpd successfully")

        # Now that we have session, we got access to bash. Let's extract public data from it
        self._attacker.execute_action("192.168.0.2", "bash", action, session)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Got data out of local service")
        self.assertEqual(message.content[0].owner, "user1", "Got public data of user1")

        # Time to get private data from bash
        # But first, get access as a user1
        exploits = ExploitStore().get_exploit(service="bash", category=ExploitCategory.AUTH_MANIPULATION)
        # TODO currently there is no way for root to access user data. There are case where we may want it, there are
        #      other cases. We need to ind a good way to choose the right action
        # TODO we also need a better mechanism for exploit selection
        user_exploit = None
        for e in exploits:
            if ExploitParameterType.IDENTITY in e.parameters:
                user_exploit = e
                break

        user_action = self._actions["rit:privilege_escalation:user_privilege_escalation"]

        user_exploit.parameters[ExploitParameterType.IDENTITY].set_value("user1")
        user_action.set_exploit(user_exploit)

        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        user_auth = message.authorization

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Escalated privileges")
        self.assertEqual(user_auth.identity, "user1", "Got access as user1")

        # and now, finally, use the user1 credentials to get the private data
        self._attacker.execute_action("192.168.0.2", "bash", action, session, user_auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Got data")
        self.assertTrue(len(message.content) == 2, "Got both public and private data")

        # Try to unsuccessfully get access to lighttpd private data
        # and now, finally, use the user1 credentials to get the private data
        self._attacker.execute_action("192.168.0.2", "lighttpd", action, session, user_auth)

        self._env.resume()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Got data")
        self.assertTrue(len(message.content) == 2 and message.content[0].owner == "user1" and
                        message.content[1].owner == "user1", "Got only public data")

if __name__ == '__main__':
    unittest.main()
