import unittest
import uuid

from netaddr import IPAddress

from cyst.api.logic.access import AccessLevel, Authorization
from cyst.api.logic.action import ActionParameter, ActionParameterType
from cyst.api.logic.exploit import ExploitCategory, ExploitLocality, ExploitParameterType
from cyst.api.environment.environment import Environment
from cyst.api.environment.control import EnvironmentControl, EnvironmentState
from cyst.api.environment.configuration import ServiceParameter
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.message import StatusOrigin, StatusValue, Status
from cyst.api.environment.stores import ExploitStore
from cyst.api.network.node import Node

# from cyst.core.logic.access import AuthorizationImpl
# from cyst.core.logic.data import DataImpl
# from cyst.core.logic.exploit import ExploitImpl, VulnerableServiceImpl, ExploitParameterImpl
# from cyst.core.environment.environment import EnvironmentProxy
# from cyst.core.network.router import Router, Route
# from cyst.core.network.elements import InterfaceImpl, Endpoint, Hop
# from cyst.core.network.session import SessionImpl
# from cyst.core.network.node import NodeImpl
# from cyst.core.host.service import PassiveServiceImpl, ServiceImpl

from cyst.services.scripted_attacker.main import ScriptedAttacker


class TestAIFIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._env = Environment.create()
        cls._env.control.init()

        cls._action_list = cls._env.resources.action_store.get_prefixed("aif")
        cls._actions = {}
        for action in cls._action_list:
            cls._actions[action.id] = action

        # Function aliases to make it more readable
        create_node = cls._env.configuration.node.create_node
        create_router = cls._env.configuration.node.create_router
        create_active_service = cls._env.configuration.service.create_active_service
        create_passive_service = cls._env.configuration.service.create_passive_service
        add_service = cls._env.configuration.node.add_service
        set_service_parameter = cls._env.configuration.service.set_service_parameter
        create_interface = cls._env.configuration.node.create_interface
        add_node = cls._env.configuration.network.add_node
        add_connection = cls._env.configuration.network.add_connection
        add_route = cls._env.configuration.node.add_route
        add_interface = cls._env.configuration.node.add_interface
        create_session = cls._env.configuration.network.create_session
        public_data = cls._env.configuration.service.public_data
        private_data = cls._env.configuration.service.private_data
        create_data = cls._env.configuration.service.create_data
        private_authorizations = cls._env.configuration.service.private_authorizations
        add_exploit = cls._env.configuration.exploit.add_exploit
        create_exploit = cls._env.configuration.exploit.create_exploit
        create_vulnerable_service = cls._env.configuration.exploit.create_vulnerable_service
        create_exploit_parameter = cls._env.configuration.exploit.create_exploit_parameter

        # A passive node that:
        # - is running two services - ssh and a http
        # - has two users and a root
        # - contains interesting data data can be shared
        target = create_node("target1")
        all_auth = cls._env.policy.create_authorization("root", ["target1"], ["*"], AccessLevel.ELEVATED)
        cls._env.policy.add_authorization(all_auth)

        # SSH service, with valid authentication grants a user access to the system
        # Exploiting the service grants a root access to the system
        ssh_service = create_passive_service("openssh", owner="ssh", version="8.1.0", service_access_level=AccessLevel.ELEVATED)
        # SSH enables session creation
        set_service_parameter(ssh_service.passive_service, ServiceParameter.ENABLE_SESSION, True)
        # Sessions can be opened by ordinary users and root
        set_service_parameter(ssh_service.passive_service, ServiceParameter.SESSION_ACCESS_LEVEL, AccessLevel.LIMITED)
        # make the ssh authorization available to the attacker
        cls._ssh_auth_1 = cls._env.policy.create_authorization("user1", ["target1"], ["openssh"], AccessLevel.LIMITED)
        cls._ssh_auth_2 = cls._env.policy.create_authorization("user2", ["target1"], ["openssh"], AccessLevel.LIMITED)
        cls._env.policy.add_authorization(cls._ssh_auth_1, cls._ssh_auth_2)

        # Bash service, accessible only locally
        bash_service = create_passive_service("bash", owner="bash", version="5.0.0", local=True, service_access_level=AccessLevel.LIMITED)
        # TODO Bash and other services should probably support local code execution exploits
        bash_auth_1 = cls._env.policy.create_authorization("user1", ["target1"], ["bash"], AccessLevel.LIMITED)
        bash_auth_2 = cls._env.policy.create_authorization("user2", ["target1"], ["bash"], AccessLevel.LIMITED)
        cls._env.policy.add_authorization(bash_auth_1, bash_auth_2)

        # Setting bash as a shell - this way, any successful code-execution exploits to other services will also be
        # given an access to the bash authorizations
        cls._env.configuration.node.set_shell(target, bash_service)

        public_data(bash_service.passive_service).append(create_data(None, "user1", "Worthless data"))
        private_data(bash_service.passive_service).append(create_data(None, "user1", "Interesting data, somehow hidden in bash"))

        # HTTP service provides a list of users when queried for information. May get system access with exploit
        # Authorizations only added as a public data and are not registered in the policy, because on their own, they do not
        # grant any access.
        http_service = create_passive_service("lighttpd", owner="lighttpd", version="1.4.54", service_access_level=AccessLevel.LIMITED)
        http_auth_1 = cls._env.policy.create_stub_authorization("user1", ["target1"])
        http_auth_2 = cls._env.policy.create_stub_authorization("user2", ["target1"])
        cls._env.policy.add_authorization(http_auth_1, http_auth_2)

        # Add some public and private data to the service
        public_data(http_service.passive_service).append(create_data(None, "user1", "Completely useless data"))
        private_data(http_service.passive_service).append(create_data(None, "user1", "Much more interesting piece of information"))
        private_authorizations(http_service.passive_service).extend([http_auth_1, http_auth_2])

        # Add system exploitability
        exploit1 = create_exploit("http_exploit", [create_vulnerable_service("lighttpd", "1.4.54")], ExploitLocality.REMOTE, ExploitCategory.CODE_EXECUTION)
        exploit2 = create_exploit("http_root_exploit", [create_vulnerable_service("lighttpd", "1.4.54")], ExploitLocality.REMOTE, ExploitCategory.CODE_EXECUTION,
                                  create_exploit_parameter(ExploitParameterType.ENABLE_ELEVATED_ACCESS, "TRUE", immutable=True))
        exploit3 = create_exploit("ftp_exploit", [create_vulnerable_service("vsftpd", "3.0.3")], ExploitLocality.REMOTE, ExploitCategory.CODE_EXECUTION)
        exploit4 = create_exploit("bash_user_exploit", [create_vulnerable_service("bash", "5.0.0")], ExploitLocality.LOCAL,
                                  ExploitCategory.AUTH_MANIPULATION, create_exploit_parameter(ExploitParameterType.IDENTITY),
                                  create_exploit_parameter(ExploitParameterType.ENABLE_ELEVATED_ACCESS, "FALSE", immutable=True))
        exploit5 = create_exploit("bash_root_exploit", [create_vulnerable_service("bash", "5.0.0")], ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION,
                                  create_exploit_parameter(ExploitParameterType.ENABLE_ELEVATED_ACCESS, "TRUE", immutable=True))
        exploit6 = create_exploit("bash_master_exploit", [create_vulnerable_service("bash", "5.0.0")], ExploitLocality.LOCAL,
                                  ExploitCategory.AUTH_MANIPULATION,
                                  create_exploit_parameter(ExploitParameterType.ENABLE_ELEVATED_ACCESS, "TRUE", immutable=True),
                                  create_exploit_parameter(ExploitParameterType.IMPACT_IDENTITY, "ALL", immutable=True),
                                  create_exploit_parameter(ExploitParameterType.IMPACT_NODE, "ALL", immutable=True),
                                  create_exploit_parameter(ExploitParameterType.IMPACT_SERVICE, "ALL", immutable=True))

        add_exploit(exploit1, exploit2, exploit3, exploit4, exploit5, exploit6)

        add_service(target, ssh_service)
        add_service(target, http_service)
        add_service(target, bash_service)

        # Place a router in front of the target
        router = create_router("router1", cls._env.messaging)
        add_interface(router, create_interface("192.168.0.1", "255.255.255.0"))

        # Create an attacker
        attacker_node = create_node("attacker_node")
        attacker_service = create_active_service("scripted_attacker", "attacker", "scripted_attacker", attacker_node)
        add_service(attacker_node, attacker_service)
        cls._attacker = ScriptedAttacker.cast_from(attacker_service)

        cls._env.control.add_pause_on_response("attacker_node.scripted_attacker")

        # Connect the environment pieces
        add_node(target)
        add_node(router)
        add_node(attacker_node)

        # TODO change this to env method, once this is merged from bronze_butler branch
        add_connection(router, target, net="192.168.0.0/24")
        add_connection(router, attacker_node, net="192.168.0.0/24")

    # Test correct handling of active scans, namely:
    # - successful scanning of a live machine
    # - unsuccessful scanning of non-existing machine
    # - scanning of an un-routable target
    def test_0000_active_recon_host_scan(self) -> None:

        action = self._actions["aif:active_recon:host_discovery"]
        self._attacker.execute_action("192.168.0.2", "", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.SUCCESS), "Liveliness confirmed")

        self._attacker.execute_action("192.168.0.6", "", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NETWORK, StatusValue.FAILURE), "Host unreachable")

        self._attacker.execute_action("192.168.1.6", "", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NETWORK, StatusValue.FAILURE), "Host un-routable")

    # Test correct gathering of running services
    def test_0001_active_recon_service_scan(self) -> None:

        action = self._actions["aif:active_recon:service_discovery"]
        self._attacker.execute_action("192.168.0.2", "", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.SUCCESS), "Services disclosed")
        self.assertEqual(message.content, ["openssh", "lighttpd", "bash"])

    # Test getting correct versions of services running on the target and an attempt to get a version of a
    # service, which is not running
    def test_0002_active_recon_vulnerability_discovery(self) -> None:

        action = self._actions["aif:active_recon:vulnerability_discovery"]
        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Potential vulnerabilities disclosed")
        self.assertEqual(message.content, ["lighttpd-1.4.54"])

        self._attacker.execute_action("192.168.0.2", "nonexisting_service", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Vulnerability of non-existent service not disclosed")

    # Test extraction of publicly available information from the http service
    def test_0003_active_recon_information_discovery(self) -> None:

        action = self._actions["aif:active_recon:information_discovery"]
        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Information disclosed")

        counter = 0
        authorizations = message.content
        for auth in authorizations:
            # The service contains public data as well
            if isinstance(auth, Authorization):
                self.assertEqual(auth.identity, "user" + str(counter + 1), "Correct identity returned")
                self.assertTrue(self._env.policy.decide("target1", "", AccessLevel.NONE, auth), "Authorization for correct target received")
                counter += 1

    def test_0004_ensure_access_command_and_control(self) -> None:

        action = self._actions["aif:ensure_access:command_and_control"]

        # Three variations of the c&c action - with authorization, with exploit (with or without wrong authorization)
        #                                      and without anything + some errors because of omissions
        self._attacker.execute_action("192.168.0.2", "", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because service not specified")

        self._attacker.execute_action("192.168.0.2", "nonexistent_service", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because wrong service specified")

        self._attacker.execute_action("192.168.0.2", "openssh", action)

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because neither auth nor exploit were provided")

        self._attacker.execute_action("192.168.0.2", "openssh", action, authorization=self._ssh_auth_1)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Correctly established a session")
        self.assertTrue(isinstance(message.content, Node), "Got a node view of the target")
        self.assertEqual(message.session.end, IPAddress("192.168.0.2"))

        # Create dud authorization, that fails because of wrong access token
        dud_ssh_auth = self._env.policy.create_stub_authorization("user2", ["target1"], ["ssh"], AccessLevel.LIMITED)
        good_exploit = self._env.resources.exploit_store.get_exploit(service="lighttpd", category=ExploitCategory.CODE_EXECUTION)[0]
        action.set_exploit(good_exploit)

        self._attacker.execute_action("192.168.0.2", "lighttpd", action, authorization=dud_ssh_auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Correctly established a session")
        self.assertTrue(isinstance(message.content, Node), "Got a node view of the target")
        self.assertEqual(message.session.end, IPAddress("192.168.0.2"))
        self.assertEqual(message.authorization.identity, "lighttpd", "Got correct identity for newly created authorization")

        # Bad exploit used
        bad_exploit = self._env.resources.exploit_store.get_exploit(service="vsftpd")[0]
        action.set_exploit(bad_exploit)

        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((result, state), (True, EnvironmentState.PAUSED), "Task ran and was successfully paused.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), "Wrong exploit used")

    def test_0005_privilege_escalation_user_and_root_privilege_escalation(self) -> None:

        cc_action = self._actions["aif:ensure_access:command_and_control"]
        # Clear old data from the previous test
        cc_action.set_exploit(None)
        cc_exploit = self._env.resources.exploit_store.get_exploit(service="lighttpd", category=ExploitCategory.CODE_EXECUTION)[0]

        # TODO With this, all auth manipulation exploits can be interchangeably used for user and root priv escalation
        # This should probably be done otherwise
        user_action = self._actions["aif:privilege_escalation:user_privilege_escalation"]
        user_exploit = None

        root_action = self._actions["aif:privilege_escalation:root_privilege_escalation"]
        root_exploit = None

        master_exploit = None

        auth_exploits = self._env.resources.exploit_store.get_exploit(service="bash", category=ExploitCategory.AUTH_MANIPULATION)
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

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because service not specified")

        self._attacker.execute_action("192.168.0.2", "nonexistent_service", user_action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because wrong service specified")

        # --------------------------------------------------------------------------------------------------------------
        # Establish a session using the C&C action with the lighttpd exploit
        # --------------------------------------------------------------------------------------------------------------
        cc_action.set_exploit(cc_exploit)
        self._attacker.execute_action("192.168.0.2", "lighttpd", cc_action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        session = message.session
        auth = message.authorization

        self.assertEqual(session.end, IPAddress("192.168.0.2"), "Got correct session")

        self.assertTrue(self._env.policy.decide("", "lighttpd", AccessLevel.NONE, auth), "Authorization for correct target received")
        self.assertTrue(self._env.policy.decide("", "bash", AccessLevel.NONE, auth), "Authorization for correct target received")

        # --------------------------------------------------------------------------------------------------------------
        # Sanity tests (round 2)
        # --------------------------------------------------------------------------------------------------------------
        create_exploit = self._env.configuration.exploit.create_exploit
        create_exploit_parameter = self._env.configuration.exploit.create_exploit_parameter
        create_vulnerable_service = self._env.configuration.exploit.create_vulnerable_service

        intentionally_remote_exploit = self._env.resources.exploit_store.get_exploit(service="lighttpd", category=ExploitCategory.CODE_EXECUTION)[0]
        user_action.set_exploit(intentionally_remote_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        # Result and state are discarded from now on
        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because non-local exploit used")

        # --------------------------------------------------------------------------------------------------------------
        # Don't try this at home
        user_action.set_exploit(create_exploit("dummy_local_exploit", None, locality=ExploitLocality.LOCAL, category=ExploitCategory.DATA_MANIPULATION))

        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because exploit of wrong category used")

        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(create_exploit("too_many_param_local_exploit", None, ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION,
                                               create_exploit_parameter(ExploitParameterType.NONE), create_exploit_parameter(ExploitParameterType.NONE)))
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because exploit uses two parameters")

        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(create_exploit("wrong_param_local_exploit", None, ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION,
                                create_exploit_parameter(ExploitParameterType.NONE)))
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because exploit uses wrong parameter type")

        # --------------------------------------------------------------------------------------------------------------
        user_exploit.parameters[ExploitParameterType.IDENTITY].set_value("user1")
        user_action.set_exploit(user_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.ERROR), "Failed because no session specified")

        # --------------------------------------------------------------------------------------------------------------
        self._attacker.execute_action("192.168.0.2", "openssh", user_action, session, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), "Failed because wrong authentication specified")

        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(create_exploit("old_bash_user_exploit", [create_vulnerable_service("bash", "3.0.0")], ExploitLocality.LOCAL, ExploitCategory.AUTH_MANIPULATION, create_exploit_parameter(ExploitParameterType.IDENTITY)))
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), "Failed because of unusable exploit")

        # --------------------------------------------------------------------------------------------------------------
        user_exploit.parameters[ExploitParameterType.IDENTITY].set_value("user3")
        user_action.set_exploit(user_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), "Failed because of unavailable user")

        # --------------------------------------------------------------------------------------------------------------
        # Successful user exploit
        # --------------------------------------------------------------------------------------------------------------
        user_exploit.parameters[ExploitParameterType.IDENTITY].set_value("user1")
        user_action.set_exploit(user_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "We correctly commenced the exploit")
        self.assertEqual(message.authorization.identity, "user1", "Got authorization for requested user")

        # --------------------------------------------------------------------------------------------------------------
        # Successful root exploit
        # --------------------------------------------------------------------------------------------------------------
        root_action.set_exploit(root_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", root_action, session, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "We correctly commenced the exploit")
        self.assertEqual(message.authorization.identity, "root", "Got authorization for root")
        self.assertTrue(self._env.policy.decide("", "", AccessLevel.ELEVATED, auth), "Got elevated access level")

        # --------------------------------------------------------------------------------------------------------------
        # Test master exploit
        # --------------------------------------------------------------------------------------------------------------
        user_action.set_exploit(master_exploit)
        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "We correctly commenced the exploit")
        self.assertEqual(message.authorization.identity, "*", "Got authorization for anyone")
        # TODO There is no sensible way to test these from user code. However, the authorization handling still has to be revised.
        #      Until then the code is commented out
        # self.assertEqual(AuthorizationImpl.cast_from(message.authorization).nodes, ["*"], "Got authorization for anyone")
        # self.assertEqual(AuthorizationImpl.cast_from(message.authorization).services, ["*"], "Got authorization for anyone")
        # self.assertEqual(AuthorizationImpl.cast_from(message.authorization).access_level, AccessLevel.LIMITED, "Got elevated access level")

    def test_0006_disclosure_data_exfiltration(self) -> None:

        action = self._actions["aif:disclosure:data_exfiltration"]

        # --------------------------------------------------------------------------------------------------------------
        # Sanity tests
        # --------------------------------------------------------------------------------------------------------------
        self._attacker.execute_action("192.168.0.2", "", action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because service not specified")

        self._attacker.execute_action("192.168.0.2", "nonexistent_service", action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because wrong service specified")

        self._attacker.execute_action("192.168.0.2", "bash", action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because local service specified")

        # --------------------------------------------------------------------------------------------------------------
        # Disclose publicly available data
        self._attacker.execute_action("192.168.0.2", "lighttpd", action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Got public data from lighttpd service")
        self.assertTrue(type(message.content) is list and len(message.content) == 1 and message.content[0].owner == "user1", "Got correct data")

        # Exploit httpd to get access
        remote_exploit = self._env.resources.exploit_store.get_exploit(service="lighttpd")[0]
        cc_action = self._actions["aif:ensure_access:command_and_control"]
        cc_action.set_exploit(remote_exploit)

        self._attacker.execute_action("192.168.0.2", "lighttpd", cc_action)

        self._env.control.run()
        message = self._attacker.get_last_response()

        session = message.session
        auth = message.authorization

        # At this point, we can guess which users are present on the system from message.content, which is a NodeView.
        # TODO However, there is no clear mapping of service -> user accounts

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Established a session")

        self.assertTrue(self._env.policy.decide("", "lighttpd", AccessLevel.NONE, auth), "Exploited lighttpd successfully")

        # Now that we have session, we got access to bash. Let's extract public data from it
        self._attacker.execute_action("192.168.0.2", "bash", action, session)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Got data out of local service")
        self.assertEqual(message.content[0].owner, "user1", "Got public data of user1")

        # Time to get private data from bash
        # But first, get access as a user1
        exploits = self._env.resources.exploit_store.get_exploit(service="bash", category=ExploitCategory.AUTH_MANIPULATION)
        # TODO currently there is no way for root to access user data. There are case where we may want it, there are
        #      other cases. We need to ind a good way to choose the right action
        # TODO we also need a better mechanism for exploit selection
        user_exploit = None
        for e in exploits:
            if ExploitParameterType.IDENTITY in e.parameters:
                user_exploit = e
                break

        user_action = self._actions["aif:privilege_escalation:user_privilege_escalation"]

        user_exploit.parameters[ExploitParameterType.IDENTITY].set_value("user1")
        user_action.set_exploit(user_exploit)

        self._attacker.execute_action("192.168.0.2", "bash", user_action, session, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        user_auth = message.authorization

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Escalated privileges")
        self.assertEqual(user_auth.identity, "user1", "Got access as user1")

        # and now, finally, use the user1 credentials to get the private data
        self._attacker.execute_action("192.168.0.2", "bash", action, session, user_auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Got data")
        self.assertTrue(len(message.content) == 2, "Got both public and private data")

        # Try to unsuccessfully get access to lighttpd private data
        self._attacker.execute_action("192.168.0.2", "lighttpd", action, session, user_auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Got data")
        self.assertTrue(len(message.content) == 1 and message.content[0].owner == "user1", "Got only the public data")

    def test_0007_destroy_data_destruction(self) -> None:

        action_destruction = self._actions["aif:destroy:data_destruction"]
        action_exfiltration = self._actions["aif:disclosure:data_exfiltration"]
        action_cc = self._actions["aif:ensure_access:command_and_control"]
        action_cc.set_exploit(self._env.resources.exploit_store.get_exploit(service="lighttpd")[0])

        # --------------------------------------------------------------------------------------------------------------
        # Sanity tests
        # --------------------------------------------------------------------------------------------------------------
        self._attacker.execute_action("192.168.0.2", "", action_destruction)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because service not specified")

        self._attacker.execute_action("192.168.0.2", "nonexistent_service", action_destruction)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because wrong service specified")

        self._attacker.execute_action("192.168.0.2", "bash", action_destruction)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Failed because local service specified")

        # --------------------------------------------------------------------------------------------------------------
        # Attempt to remove data without any authorization
        self._attacker.execute_action("192.168.0.2", "lighttpd", action_destruction)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), "Unauthorized attempt to delete accessible data")

        # --------------------------------------------------------------------------------------------------------------
        # Attempt to remove data without proper authorization
        self._attacker.execute_action("192.168.0.2", "lighttpd", action_cc)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Gained session to the target")

        view = message.content
        auth = message.authorization
        sess = message.session

        # Get IDs of public data
        for datum in view.services[message.src_service].public_data:
            action_destruction.add_parameters(ActionParameter(ActionParameterType.ID, str(datum.id)))

        self._attacker.execute_action("192.168.0.2", "lighttpd", action_destruction, sess, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        # Check if the data vanished
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Destruction commenced successfully")

        self._attacker.execute_action("192.168.0.2", "lighttpd", action_exfiltration, sess, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Exfiltration successful")
        self.assertTrue(len(message.content) == 1, "Nothing was deleted")

        # --------------------------------------------------------------------------------------------------------------
        # Attempt to remove data with authorization
        exploits = self._env.resources.exploit_store.get_exploit(service="bash", category=ExploitCategory.AUTH_MANIPULATION)

        user_exploit = None
        for e in exploits:
            if ExploitParameterType.IDENTITY in e.parameters:
                user_exploit = e
                break

        user_action = self._actions["aif:privilege_escalation:user_privilege_escalation"]

        user_exploit.parameters[ExploitParameterType.IDENTITY].set_value("user1")
        user_action.set_exploit(user_exploit)

        self._attacker.execute_action("192.168.0.2", "bash", user_action, sess, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        user_auth = message.authorization

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Escalated privileges")
        self.assertEqual(user_auth.identity, "user1", "Got access as user1")

        # Get data from bash to extract user ids for subsequent deletion
        self._attacker.execute_action("192.168.0.2", "bash", action_exfiltration, sess, user_auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Got data")

        action_destruction.parameters.clear()
        for datum in message.content:
            action_destruction.add_parameters(ActionParameter(ActionParameterType.ID, str(datum.id)))

        # Delete the data
        self._attacker.execute_action("192.168.0.2", "bash", action_destruction, sess, user_auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Performed data deletion")

        # Check if the data really vanished
        self._attacker.execute_action("192.168.0.2", "bash", action_exfiltration, sess, user_auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Exfiltrated data")
        self.assertTrue(len(message.content) == 0, "Data really deleted")

    def test_0008_ensure_access_lateral_movement(self) -> None:
        action_lm = self._actions["aif:ensure_access:lateral_movement"]

        # Sanity check - no action without session
        self._attacker.execute_action("192.168.0.2", "", action_lm)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "No lateral movement without a session")

        # Get the session
        action_cc = self._actions["aif:ensure_access:command_and_control"]
        action_cc.set_exploit(self._env.resources.exploit_store.get_exploit("http_exploit")[0])

        self._attacker.execute_action("192.168.0.2", "lighttpd", action_cc)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Gained session to the target")

        sess = message.session
        auth = message.authorization

        # Run the action without an attacker id
        self._attacker.execute_action("192.168.0.2", "", action_lm, sess, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "No ID of an attacker to instantiate specified")

        # Set the wrong ID
        action_lm.add_parameters(ActionParameter(ActionParameterType.ID, "NonexistentAttacker"))

        self._attacker.execute_action("192.168.0.2", "", action_lm, sess, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.ERROR), "Wrong attacker ID specified")

        # Set the correct ID but don't have adequate privileges
        action_lm.parameters.clear()
        action_lm.add_parameters(ActionParameter(ActionParameterType.ID, "scripted_attacker"))

        self._attacker.execute_action("192.168.0.2", "", action_lm, sess, auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.FAILURE), "Insufficient privileges to run the attacker")

        # Get the root-level session
        # Get the session
        action_root_cc = self._actions["aif:ensure_access:command_and_control"]
        action_root_cc.set_exploit(self._env.resources.exploit_store.get_exploit("http_root_exploit")[0])

        self._attacker.execute_action("192.168.0.2", "lighttpd", action_root_cc)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "Gained session to the target")

        root_sess = message.session
        root_auth = message.authorization

        # And finally launch the attacker on the remote system
        self._attacker.execute_action("192.168.0.2", "", action_lm, root_sess, root_auth)

        self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual(message.status, Status(StatusOrigin.NODE, StatusValue.SUCCESS), "Successfully launched an attacker instance")
        self.assertTrue(type(message.content is Node), "Got correct response")

        # TODO need to resolve the issue with active service names vs. ids. Mutliple services would make a mess
        found = False
        for service in message.content.services:
            if service.startswith("scripted_attacker"):
                found = True

        self.assertTrue(found, "Attacker service was correctly started")


if __name__ == '__main__':
    unittest.main()
