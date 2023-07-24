import unittest

from cyst.api.configuration import *
from cyst.api.environment.environment import Environment
from cyst.api.logic.access import AuthenticationProvider, AuthenticationToken, Authorization, AuthenticationTarget
from cyst.api.logic.access import AuthenticationProviderType, AuthenticationTokenType, AuthenticationTokenSecurity
from cyst.api.network.node import Node

from cyst.core.logic.access import AuthenticationProviderImpl
from cyst.core.logic.access import AuthenticationTokenImpl

""" Environment configuration """
local_password_auth = AuthenticationProviderConfig \
        (
        provider_type=AuthenticationProviderType.LOCAL,
        token_type=AuthenticationTokenType.PASSWORD,
        token_security=AuthenticationTokenSecurity.SEALED,
        timeout=30
    )

remote_email_auth = AuthenticationProviderConfig \
        (
        provider_type=AuthenticationProviderType.REMOTE,
        token_type=AuthenticationTokenType.PASSWORD,
        token_security=AuthenticationTokenSecurity.SEALED,
        ip=IPAddress("192.168.0.2"),
        timeout=60
    )

proxy_sso = AuthenticationProviderConfig \
        (
        provider_type=AuthenticationProviderType.PROXY,
        token_type=AuthenticationTokenType.PASSWORD,
        token_security=AuthenticationTokenSecurity.SEALED,
        ip=IPAddress("192.168.0.3"),
        timeout=30
    )

# authentication_providers = [local_password_auth, remote_email_auth, proxy_sso]

ssh_service = PassiveServiceConfig(
    type="ssh",
    owner="ssh",
    version="5.1.4",
    local=False,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[local_password_auth("ssh_service_local_auth_id")],
    access_schemes=[AccessSchemeConfig(
        authentication_providers=["ssh_service_local_auth_id"],
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
    type="email_srv",
    owner="email",
    version="3.3.3",
    local=False,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[remote_email_auth]
)

my_custom_service = PassiveServiceConfig(
    type="my_custom_service",
    owner="custom",
    version="1.0.0",
    local=True,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[local_password_auth("my_custom_service_auth_id")],
    access_schemes=[
        AccessSchemeConfig(
            authentication_providers=["my_custom_service_auth_id", remote_email_auth.id],
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
    id="my_sso_domain"
)

sso_service = PassiveServiceConfig(
    type="sso_service",
    owner="sso",
    version="1.2.3",
    local=False,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[proxy_sso]
)

web_server = PassiveServiceConfig(
    type="lighttpd",
    owner="lighttpd",
    version="8.1.4",
    local=False,
    access_level=AccessLevel.LIMITED,
    authentication_providers=[],
    access_schemes=[
        AccessSchemeConfig(
            authentication_providers=[proxy_sso.id],
            authorization_domain=my_sso_domain
        )
    ]
)

email_server = NodeConfig(id="email_server_node", active_services=[], passive_services=[email_srv], shell="bash",
                          traffic_processors=[],
                          interfaces=[InterfaceConfig(IPAddress("192.168.0.2"), IPNetwork("192.168.0.1/24"))])
sso_server = NodeConfig(id="sso_server_node", active_services=[], passive_services=[sso_service], shell="bash",
                        traffic_processors=[],
                        interfaces=[InterfaceConfig(IPAddress("192.168.0.3"), IPNetwork("192.168.0.1/24"))])
target = NodeConfig(id="target_node", active_services=[], passive_services=[ssh_service, my_custom_service, web_server],
                    traffic_processors=[],
                    shell="bash", interfaces=[InterfaceConfig(IPAddress("192.168.0.4"), IPNetwork("192.168.0.1/24"))])

router1 = RouterConfig(
    interfaces=[
        InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.1/24"), index=0),
        InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.1/24"), index=1),
        InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.1/24"), index=2),
        InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.1/24"), index=3)
    ],
    traffic_processors=[],
    id="router1"
)

connections = [
    ConnectionConfig("target_node", 0, "router1", 1),
    ConnectionConfig("sso_server_node", 0, "router1", 2),
    ConnectionConfig("email_server_node", 0, "router1", 3)
]


class AuthenticationProcessTestSSH(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.env = Environment.create().configure(email_server, sso_server, target, router1, *connections)

        node = cls.env.configuration.general.get_object_by_id("target_node", Node)
        service = next(filter(lambda x: x.name == "ssh", node.services.values()))
        provider = cls.env.configuration.general.get_object_by_id("ssh_service_local_auth_id",
                                                                  AuthenticationProvider)
        token = None
        if isinstance(provider, AuthenticationProviderImpl):
            token = next(iter(provider._tokens)).token

        assert None not in [node, service, provider, token]

        cls.node = node
        cls.service = service
        cls.token = token

    def test_000_invalid_token(self):
        result = self.env.configuration.access.evaluate_token_for_service(self.service,  # the method is not in the Environment API, so we need to know we are dealing with an _Environment, is that ok?
                                                                          AuthenticationTokenImpl(
                                                                              AuthenticationTokenType.PASSWORD,
                                                                              AuthenticationTokenSecurity.OPEN,
                                                                              identity="user1",
                                                                              is_local=True
                                                                          ),  # everything ok except id
                                                                          self.node,
                                                                          IPAddress("0.0.0.0"))

        self.assertIsNone(result, "Process returned an object for a bad token")

    def test_001_valid_token_get_auth(self):
        result = self.env.configuration.access.evaluate_token_for_service(self.service,
                                                                          self.token,
                                                                          self.node,
                                                                          IPAddress("0.0.0.0"))

        self.assertIsInstance(result, Authorization, "The object is not an authorization")
        self.assertEqual(result.identity, self.token.identity, "Identities of token and auth do not match")
        if result.identity == "root":
            self.assertEqual(result.access_level, AccessLevel.ELEVATED, "Mismatched access level")
        else:
            self.assertEqual(result.access_level, AccessLevel.LIMITED, "Mismatched access level")


class AuthenticationProcessTestCustomService(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.env = Environment.create().configure(email_server, sso_server, target, router1, *connections)

        node = cls.env.configuration.general.get_object_by_id("target_node", Node)
        service = next(filter(lambda x: x.name == "my_custom_service", node.services.values()))
        provider = cls.env.configuration.general.get_object_by_id("my_custom_service_auth_id",
                                                                  AuthenticationProvider)
        token = None
        if isinstance(provider, AuthenticationProviderImpl):
            # TODO: It is confusing that with the change that lead to stte tracking of tokens the name remained _tokens
            #       It should be token states to prevent confusion and accidental errors.
            token = next(iter(provider._tokens)).token

        assert None not in [node, service, provider, token]

        cls.node = node
        cls.service = service
        cls.token = token

    def test_000_valid_token_get_next_target(self):
        result = self.env.configuration.access.evaluate_token_for_service(self.service,
                                                                          self.token,
                                                                          self.node,
                                                                          IPAddress("0.0.0.0"))

        target_service = next(filter(lambda s: s.name == "email_srv",
                                     self.env.configuration.general.get_object_by_id(
                                         "email_server_node", Node).services.values())
                              )

        self.assertIsInstance(result, AuthenticationTarget, "The object is not an AuthenticationTarget")
        self.assertEqual(result.service, target_service.id, "Target service mismatch")
        self.assertEqual(result.address, remote_email_auth.ip, "Target ip mismatch")

    def test_001_invalid_token(self):
        result = self.env.configuration.access.evaluate_token_for_service(self.service,
                                                                          AuthenticationTokenImpl(
                                                                              AuthenticationTokenType.PASSWORD,
                                                                              AuthenticationTokenSecurity.OPEN,
                                                                              identity="user1",
                                                                              is_local=True
                                                                          ),  # everything ok except id
                                                                          self.node,
                                                                          IPAddress("0.0.0.0"))

        self.assertIsNone(result, "Process returned an object for a bad token")


class AuthenticationAccessManipulationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.env = Environment.create().configure(email_server, sso_server, target, router1, *connections)

        node = cls.env.configuration.general.get_object_by_id("target_node", Node)

        service_2fa = next(filter(lambda x: x.name == "my_custom_service", node.services.values()))
        service_local_1fa = next(filter(lambda x: x.name == "ssh", node.services.values()))

        provider = cls.env.configuration.general.get_object_by_id("ssh_service_local_auth_id",
                                                                  AuthenticationProviderImpl)
        token = provider.get_token_by_identity("user1")

        assert None not in [node, service_2fa, service_local_1fa, provider, token]

        cls.node = node
        cls.provider = provider
        cls.token = token
        cls.service_local_1fa = service_local_1fa
        cls.service_2fa = service_2fa

        # improve readibility
        cls.create_service_access = cls.env.configuration.access.create_service_access
        cls.modify_existing_access = cls.env.configuration.access.modify_existing_access

    def test_000_add_account(self) -> None:
        identity = "intruder1"
        result = self.create_service_access(self.service_local_1fa, identity, AccessLevel.ELEVATED)

        self.assertIsNotNone(result, "Access creation should succeed")
        assert result is not None # mypy
        self.assertIsInstance(result[0], AuthenticationToken, "The result is not an authentication token")

        token = result[0]
        self.assertEqual(token.identity, identity, f"Resulting token's identity should be {identity}")
        self.assertTrue(self.provider.token_is_registered(token), "Token should be registered")

        result = self.env.configuration.access.evaluate_token_for_service(self.service_local_1fa,
                                                                          token,
                                                                          self.node,
                                                                          IPAddress("0.0.0.0"))

        self.assertIsInstance(result, Authorization, "Resulting object should be authorization")

    def test_001_add_existing_account(self) -> None:
        result = self.create_service_access(self.service_local_1fa, "user1", AccessLevel.ELEVATED)
        self.assertIsNone(result, "Access creation with existing account should fail")

    def test_002_add_account_with_token(self) -> None:
        identity = "intruder2"
        # Provider parameters: PASSWORD, SEALED, LOCAL
        token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.SEALED,
                                        identity, True)._set_content("pass")
        result = self.create_service_access(self.service_local_1fa, identity, AccessLevel.ELEVATED, [token])

        self.assertIsNotNone(result, "Access creation should succeed")
        self.assertTrue(self.provider.token_is_registered(token), "Token should be registered")
        self.assertEqual(result[0], token, "Token should be the one supplied")

        result = self.env.configuration.access.evaluate_token_for_service(self.service_local_1fa,
                                                                          token,
                                                                          self.node,
                                                                          IPAddress("0.0.0.0"))

        self.assertIsInstance(result, Authorization, "Resulting object should be authorization")

    def test_003_add_acount_with_invalid_token(self) -> None:
        identity = "intruder3"
        invalid_token = AuthenticationTokenImpl(AuthenticationTokenType.BIOMETRIC, AuthenticationTokenSecurity.SEALED,
                                                identity, True)._set_content("pass")
        result = self.create_service_access(self.service_local_1fa, identity, AccessLevel.ELEVATED, [invalid_token])

        self.assertIsNone(result, "Access creation should not succeed")

    def test_004_modify_account(self) -> None:
        # Two rounds of authentication with modify inbetween
        identity = self.token.identity
        auth_before = self.env.configuration.access.evaluate_token_for_service(self.service_local_1fa,
                                                                               self.token,
                                                                               self.node,
                                                                               IPAddress("0.0.0.0"))
        self.assertIsInstance(auth_before, Authorization, "Resulting object should be authorization")

        result = self.modify_existing_access(self.service_local_1fa, identity, AccessLevel.ELEVATED)
        self.assertTrue(result, "Access creation should succeed")

        auth_after: Authorization = self.env.configuration.access.evaluate_token_for_service(self.service_local_1fa,
                                                                                             self.token,
                                                                                             self.node,
                                                                                             IPAddress("0.0.0.0"))
        self.assertIsInstance(auth_after, Authorization, "Resulting object should be authorization")

        self.assertGreater(auth_after.access_level, auth_before.access_level, "Access level should be higher")

    def test_005_modify_non_existent_account(self) -> None:
        identity = "user_non_existent"

        result = self.modify_existing_access(self.service_local_1fa, identity, AccessLevel.ELEVATED)
        self.assertTrue(not result, "Access creation should not succeed")

    def test_006_add_account_MF(self) -> None:
        # TODO: non-local providers are not yet implemented
        identity = "intruder"
        result = self.create_service_access(self.service_2fa, identity, AccessLevel.ELEVATED)

        self.assertIsNone(result, "Access creation should fail, for now")
        # self.assertIsNotNone(result, "Access creation should succeed")


class AuxiliaryTest(unittest.TestCase):

    def test_000_test_auth_provider_copy(self) -> None:
        local_password_auth_copy = local_password_auth()
        self.assertNotEqual(local_password_auth_copy.id, local_password_auth.id, "Authentication provider copy does not share ID")
