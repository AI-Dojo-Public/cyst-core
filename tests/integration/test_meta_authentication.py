import unittest
import uuid

from cyst.api.configuration import *
from cyst.api.environment.control import EnvironmentState
from cyst.api.environment.environment import Environment
from cyst.api.environment.message import Status, StatusOrigin, StatusValue, StatusDetail
from cyst.api.host.service import Service
from cyst.api.logic.access import AuthenticationProviderType, AuthenticationTokenType, AuthenticationTokenSecurity

from cyst.api.logic.access import AuthenticationProvider, Authorization, AuthenticationTarget
from cyst_services.scripted_actor.main import ScriptedActorControl

from cyst.platform.logic.access import AuthenticationTokenImpl

# TODO: These tests should be inside test_meta

"""Environment configuration"""
local_password_auth = AuthenticationProviderConfig(
    provider_type=AuthenticationProviderType.LOCAL,
    token_type=AuthenticationTokenType.PASSWORD,
    token_security=AuthenticationTokenSecurity.SEALED,
    timeout=30
)

remote_email_auth = AuthenticationProviderConfig(
    provider_type=AuthenticationProviderType.REMOTE,
    token_type=AuthenticationTokenType.PASSWORD,
    token_security=AuthenticationTokenSecurity.SEALED,
    ip=IPAddress("192.168.0.2"),
    timeout=60
)

proxy_sso = AuthenticationProviderConfig(
    provider_type=AuthenticationProviderType.PROXY,
    token_type=AuthenticationTokenType.PASSWORD,
    token_security=AuthenticationTokenSecurity.SEALED,
    ip=IPAddress("192.168.0.3"),
    timeout=30
)

ssh_service = PassiveServiceConfig(
    name="ssh",
    owner="ssh",
    version="5.1.4",
    local=False,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[local_password_auth(ref="ssh_service_local_auth_ref", id="ssh_service_local_auth_id")],
    access_schemes=[AccessSchemeConfig(
        authentication_providers=["ssh_service_local_auth_ref"],
        authorization_domain=AuthorizationDomainConfig(
            type=AuthorizationDomainType.LOCAL,
            authorizations=[
                AuthorizationConfig("user1", AccessLevel.LIMITED),
                AuthorizationConfig("user2", AccessLevel.LIMITED),
                AuthorizationConfig("root", AccessLevel.ELEVATED)
            ]
        )
    )]
)

email_srv = PassiveServiceConfig(
    name="email_srv",
    owner="email",
    version="3.3.3",
    local=False,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[remote_email_auth]
)

my_custom_service = PassiveServiceConfig(
    name="my_custom_service",
    owner="custom",
    version="1.0.0",
    local=True,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[local_password_auth("my_custom_service_auth_id")],
    access_schemes=[
        AccessSchemeConfig(
            authentication_providers=["my_custom_service_auth_id", remote_email_auth.ref],
            authorization_domain=AuthorizationDomainConfig(
                type=AuthorizationDomainType.LOCAL,
                authorizations=[
                    AuthorizationConfig("user1", AccessLevel.LIMITED),
                    AuthorizationConfig("user2", AccessLevel.LIMITED),
                    AuthorizationConfig("root", AccessLevel.ELEVATED)
                ]
            )
        )
    ]
)

my_sso_domain = AuthorizationDomainConfig(
    type=AuthorizationDomainType.FEDERATED,
    authorizations=[
        FederatedAuthorizationConfig(
            "user1", AccessLevel.LIMITED, ["node1", "node2"], ["lighttpd"]
        )
    ],
    name="my_sso_domain"
)

sso_service = PassiveServiceConfig(
    name="sso_service",
    owner="sso",
    version="1.2.3",
    local=False,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[proxy_sso]
)

web_server = PassiveServiceConfig(
    name="lighttpd",
    owner="lighttpd",
    version="8.1.4",
    local=False,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[],
    access_schemes=[
        AccessSchemeConfig(
            authentication_providers=[proxy_sso.ref],
            authorization_domain=my_sso_domain
        )
    ]
)

email_server = NodeConfig(name="email_server_node", active_services=[], passive_services=[email_srv], shell="bash",
                          traffic_processors=[],
                          interfaces=[InterfaceConfig(IPAddress("192.168.0.2"), IPNetwork("192.168.0.1/24"))])
sso_server = NodeConfig(name="sso_server_node", active_services=[], passive_services=[sso_service], shell="bash",
                        traffic_processors=[],
                        interfaces=[InterfaceConfig(IPAddress("192.168.0.3"), IPNetwork("192.168.0.1/24"))])
target = NodeConfig(name="target_node", active_services=[], passive_services=[ssh_service, my_custom_service, web_server],
                    traffic_processors=[],
                    shell="bash", interfaces=[InterfaceConfig(IPAddress("192.168.0.4"), IPNetwork("192.168.0.1/24"))])

router1 = RouterConfig(
    interfaces=[
        InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.1/24"), index=0),
        InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.1/24"), index=1),
        InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.1/24"), index=2),
        InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.1/24"), index=3)
    ],
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
    name="router1"
)

attacker1 = NodeConfig(
    active_services=[
        ActiveServiceConfig(
            type="scripted_actor",
            name="scripted_attacker",
            owner="attacker",
            access_level=AccessLevel.LIMITED,
        )
    ],
    passive_services=[],
    traffic_processors=[],
    interfaces=[
        InterfaceConfig(IPAddress("192.168.0.5"), IPNetwork("192.168.0.1/24"))
    ],
    shell="",
    name="attacker_node"
)

connections = [
    ConnectionConfig(attacker1, 0, router1, 0),
    ConnectionConfig(target, 0, router1, 1),
    ConnectionConfig(sso_server, 0, router1, 2),
    ConnectionConfig(email_server, 0, router1, 3)
]


class TestMetaAuth(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:

        #  create environment from config
        cls._env = Environment.create().configure(email_server, sso_server, target, router1, attacker1, *connections)

        # due to the fact that we don't yet have the exploits/means to extract tokens from providers,
        # get the tokens directly
        provider = cls._env.configuration.general.get_object_by_id("ssh_service_local_auth_id",
                                                                   AuthenticationProvider)

        cls._ssh_token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, "user1", True)._set_content(uuid.uuid4())
        cls._custom_token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, "user1", True)._set_content(uuid.uuid4())
        # the above will work only until new methods of tokens will be implemented

        # init the environment
        cls._env.control.init()

        cls._actions = {}

        _action_list = cls._env.resources.action_store.get_prefixed("meta")
        for action in _action_list:
            cls._actions[action.id] = action

        _action_list = cls._env.resources.action_store.get_prefixed("cyst")
        for action in _action_list:
            cls._actions[action.id] = action

        # create attacker
        attacker_service = cls._env.configuration.general.get_object_by_id("attacker_node.scripted_attacker", Service)
        assert attacker_service is not None
        cls._attacker: ScriptedActorControl = cls._env.configuration.service.get_service_interface(
            attacker_service.active_service, ScriptedActorControl)

        cls._env.control.add_pause_on_response("attacker_node.scripted_attacker")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._env.control.commit()

    def test_000_no_token_provided(self):

        action = self._actions["meta:authenticate"].copy()

        self.assertIsNotNone(action, "Authentication action unavailable")

        self._attacker.execute_action(
            "192.168.0.2",
            "email_srv",
            action,
            auth=None
        )

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((True, EnvironmentState.PAUSED), (result, state), "Task run failed.")
        self.assertEqual(message.status, Status(StatusOrigin.SERVICE,
                                                StatusValue.FAILURE,
                                                StatusDetail.AUTHENTICATION_NOT_PROVIDED),
                         "Bad state")
        self.assertEqual(message.content, "No auth token provided", "Bad error message")

    def test_001_bad_service(self):

        action = self._actions["meta:authenticate"].copy()

        self.assertIsNotNone(action, "Authentication action unavailable")

        self._attacker.execute_action(
            "192.168.0.2",
            "ssh",
            action
        )

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((True, EnvironmentState.PAUSED), (result, state), "Task run failed.")

        # Seemingly the node-service combination ischecked before the process
        # self.assertEqual(message.status, Status(StatusOrigin.SERVICE,
        #                                       StatusValue.FAILURE,
        #                                      StatusDetail.AUTHENTICATION_NOT_PROVIDED),
        #              "Authenticated when shouldnt")
        #self.assertEqual(message.content, "Service does not exist on this node", "Bad error message")

    def test_002_wrong_token(self):

        action = self._actions["meta:authenticate"].copy()

        self.assertIsNotNone(action, "Authentication action unavailable")
        action.parameters["auth_token"].value = AuthenticationTokenImpl(
                                                         AuthenticationTokenType.PASSWORD,
                                                         AuthenticationTokenSecurity.OPEN,
                                                         identity="user1",
                                                         is_local=True
                                                     )

        self._attacker.execute_action(
            "192.168.0.4",
            "ssh",
            action,
        )

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((True, EnvironmentState.PAUSED), (result, state), "Task run failed.")

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE,
                                                StatusValue.FAILURE,
                                                StatusDetail.AUTHENTICATION_NOT_APPLICABLE),
                         "Bad state")
        self.assertEqual(message.content, "Token invalid for this service", "Bad error message")

    def test_003_good_token_get_auth(self):

        action = self._actions["meta:authenticate"].copy()
        self.assertIsNotNone(action, "Authentication action unavailable")
        action.parameters["auth_token"].value = self._ssh_token


        self._attacker.execute_action(
            "192.168.0.4",
            "ssh",
            action,
        )

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((True, EnvironmentState.PAUSED), (result, state), "Task run failed.")

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE,
                                                StatusValue.SUCCESS),
                         "Bad state")
        self.assertIsInstance(message.auth, Authorization, "Bad object type")
        self.assertEqual(message.auth.identity, self._ssh_token.identity, "Bad identity")
        self.assertEqual(message.content, "Authorized", "Bad error message")

    def test_004_good_token_get_next_target(self):

        action = self._actions["meta:authenticate"].copy()
        self.assertIsNotNone(action, "Authentication action unavailable")
        action.parameters["auth_token"].value = self._custom_token

        self._attacker.execute_action(
            "192.168.0.4",
            "my_custom_service",
            action,
        )

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((True, EnvironmentState.PAUSED), (result, state), "Task run failed.")

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE,
                                                StatusValue.FAILURE,
                                                StatusDetail.AUTHENTICATION_NEXT),
                         "Bad state")
        self.assertIsInstance(message.auth, AuthenticationTarget, "Bad object type")
        self.assertEqual(message.auth.address, remote_email_auth.ip, "Bad target address")
        self.assertEqual(message.content, "Continue with next factor", "Bad error message")

    @unittest.skip("This test relies on authentication validation from cyst:network:create_session, however, currently "
                   "this action creates session no matter what. It will need to be rewritten.")
    def test_005_auto_authentication_bad_token(self):

        action = self._actions["cyst:network:create_session"].copy()
        self.assertIsNotNone(action, "Action unavailable")

        self._attacker.execute_action(
            "192.168.0.4",
            "ssh",
            action,
            auth = AuthenticationTokenImpl(
                AuthenticationTokenType.PASSWORD,
                AuthenticationTokenSecurity.OPEN,
                identity="user1",
                is_local=True
            )

        )

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((True, EnvironmentState.PAUSED), (result, state), "Task run failed.")

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE,
                                                StatusValue.FAILURE,
                                                StatusDetail.AUTHENTICATION_NOT_APPLICABLE),
                         "Bad state")
        self.assertEqual(message.content, "Token invalid for this service", "Bad error message")

    @unittest.skip("This test relies on authentication validation from cyst:network:create_session, however, currently "
                   "this action creates session no matter what. It will need to be rewritten.")
    def test_006_auto_authentication_good_token(self):

        action = self._actions["cyst:network:create_session"].copy()
        self.assertIsNotNone(action, "Action unavailable")

        self._attacker.execute_action(
            "192.168.0.4",
            "ssh",
            action,
            auth=self._ssh_token
        )

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((True, EnvironmentState.PAUSED), (result, state), "Task run failed.")
        self.assertIsInstance(message.auth, Authorization, "AuthenticationToken was not swapped for authorization")
        # There was a check for wrong authorization because of local authorization domain being used for remote
        # authorization. But because the cyst:network:create_session creates it no matter what, this check was removed
        # as it is not really related to the auto authentication anyway.

    @unittest.skip("This test relies on authentication validation from cyst:network:create_session, however, currently "
                   "this action creates session no matter what. It will need to be rewritten.")
    def test_007_auto_good_token_more_factors_remaining(self):

        action = self._actions["cyst:network:create_session"].copy()
        self.assertIsNotNone(action, "Action unavailable")

        self._attacker.execute_action(
            "192.168.0.4",
            "my_custom_service",
            action,
            auth=self._custom_token
        )

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((True, EnvironmentState.PAUSED), (result, state), "Task run failed.")

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE,
                                                StatusValue.FAILURE,
                                                StatusDetail.AUTHENTICATION_NEXT),
                         "Bad state")
        self.assertIsInstance(message.auth, AuthenticationTarget, "Bad object type")
        self.assertEqual(message.auth.address, remote_email_auth.ip, "Bad target address")
        self.assertEqual(message.content, "Continue with next factor", "Bad error message")

    @unittest.skip("This test relies on authentication validation from cyst:network:create_session, however, currently "
                   "this action creates session no matter what. It will need to be rewritten.")
    def test_008_auto_authentication_non_local_token(self):

        action = self._actions["cyst:network:create_session"].copy()
        self.assertIsNotNone(action, "Action unavailable")

        self._attacker.execute_action(
            "192.168.0.4",
            "ssh",
            action,
            auth=AuthenticationTokenImpl(
                AuthenticationTokenType.PASSWORD,
                AuthenticationTokenSecurity.OPEN,
                identity="user1",
                is_local=False
            )

        )

        result, state = self._env.control.run()
        message = self._attacker.get_last_response()

        self.assertEqual((True, EnvironmentState.PAUSED), (result, state), "Task run failed.")

        self.assertEqual(message.status, Status(StatusOrigin.SERVICE,
                                                StatusValue.FAILURE,
                                                StatusDetail.AUTHENTICATION_NOT_APPLICABLE),
                         "Bad state")
        self.assertEqual(message.content, "Auto-authentication does not work with non-local tokens", "Bad error message")
