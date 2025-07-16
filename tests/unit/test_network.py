import unittest
import uuid

from netaddr import IPAddress, IPNetwork
from typing import Tuple

from cyst.api.configuration import AuthenticationProviderConfig, PassiveServiceConfig, AccessSchemeConfig, \
    AuthorizationDomainConfig, AuthorizationDomainType, AuthorizationConfig, NodeConfig, InterfaceConfig, \
    ActiveServiceConfig, RouterConfig, ConnectionConfig, FirewallConfig, FirewallChainConfig, FirewallChainType, \
    SessionConfig
from cyst.api.configuration.network.elements import RouteConfig
from cyst.api.environment.configuration import ServiceParameter
from cyst.api.environment.environment import Environment
from cyst.api.environment.message import StatusOrigin, StatusValue, Status, Message, Request
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.host.service import Service, ActiveService
from cyst.api.logic.access import AccessLevel, AuthenticationProviderType, AuthenticationTokenType, \
    AuthenticationTokenSecurity
from cyst.api.network.elements import Route
from cyst.api.network.firewall import FirewallRule, FirewallPolicy
from cyst.api.network.node import Node

# from cyst.core.logic.access import AuthenticationTokenImpl

from cyst_services.scripted_actor.main import ScriptedActor, ScriptedActorControl


class TestInterface(unittest.TestCase):

    def test_0000_Interface(self):
        env = Environment.create()
        env.control.init()

        # Function aliases to make it more readable
        create_iface = env.configuration.node.create_interface
        set_iface = env.configuration.node.set_interface

        i1 = create_iface()

        self.assertEqual(i1.ip, None, "Empty IP constructor")
        self.assertEqual(i1.mask, None, "Empty mask constructor")

        # Setting mask without IP
        with self.assertRaises(Exception):
            set_iface(i1, mask="255.255.255.0")

        i2 = create_iface(ip="127.0.0.1")

        self.assertEqual(str(i2.ip), "127.0.0.1", "Correct IP address")

        #  "Wrong IP address"
        with self.assertRaises(Exception):
            create_iface(ip="276.0.0.1")

        # Mask without IP
        with self.assertRaises(Exception):
            create_iface(mask="255.255.255.0")

        i5 = create_iface(ip="10.0.0.2", mask="255.0.0.0")

        self.assertEqual(i5.mask, "255.0.0.0", "Correct mask counted")
        self.assertEqual(i5.gateway, IPAddress("10.0.0.1"), "Correct gateway derived")

        set_iface(i5, ip="10.0.1.9")

        self.assertEqual(i5.mask, "255.0.0.0", "Mask unchanged")
        self.assertEqual(i5.gateway, IPAddress("10.0.0.1"), "Gateway unchanged")

        set_iface(i5, mask="255.255.255.0")

        self.assertEqual(i5.gateway, IPAddress("10.0.1.1"), "Gateway recomputed")

        env.control.commit()

    def test_0001_Port(self):
        # Ports are used under the hood for the interfaces as well, so all the tests above are valid for port as
        # well. The only thing that needs to be tested is the actual code path to create the port through configuration
        # interface.
        env = Environment.create()
        env.control.init()

        port = env.configuration.node.create_port(index=-1)

        self.assertIsNotNone(port, "Port created through configuration interface")

        env.control.commit()


class TestSessions(unittest.TestCase):

    def test_0000_single_session(self):
        env = Environment.create()
        env.control.init()

        # Function aliases to make it more readable
        create_node = env.configuration.node.create_node
        create_interface = env.configuration.node.create_interface
        add_node = env.configuration.network.add_node
        add_connection = env.configuration.network.add_connection
        add_interface = env.configuration.node.add_interface
        create_session = env.configuration.network.create_session

        node1 = create_node("node1", "10.0.0.1")
        node2 = create_node("node2", "10.0.0.2")
        add_interface(node2, create_interface("10.0.1.1"))
        node3 = create_node("node3", "10.0.1.2")

        add_node(node1)
        add_node(node2)
        add_node(node3)

        add_connection(node1, node2, 0, 0)
        add_connection(node2, node3, 1, 0)

        with self.assertRaises(Exception):
            create_session("", [node1, node2, node3])

        s1 = create_session("node1", [node1, node2, node3])
        it = s1.forward_iterator

        self.assertTrue(it.has_next(), "Forward iterator has some elements")
        hop = next(it)
        self.assertEqual(hop.src.id, "node1", "Correct first iteration - source")
        self.assertEqual(hop.dst.id, "node2", "Correct first iteration - destination")
        hop = next(it)
        self.assertEqual(hop.src.id, "node2", "Correct second iteration")
        self.assertEqual(hop.dst.id, "node3", "Correct third iteration")
        self.assertFalse(it.has_next(), "Forward iterator has no elements left")
        with self.assertRaises(StopIteration):
            next(it)

        env.control.commit()

    def test_0001_multiple_sessions(self):
        env = Environment.create()
        env.control.init()

        # Function aliases to make it more readable
        create_node = env.configuration.node.create_node
        create_interface = env.configuration.node.create_interface
        add_node = env.configuration.network.add_node
        add_connection = env.configuration.network.add_connection
        add_interface = env.configuration.node.add_interface
        create_session = env.configuration.network.create_session

        node1 = create_node("node1", "10.0.0.1")
        node2 = create_node("node2", "10.0.0.2")
        add_interface(node2, create_interface("10.0.1.1"))
        node3 = create_node("node3", "10.0.1.2")
        add_interface(node3, create_interface("10.0.2.1"))
        node4 = create_node("node4", "10.0.2.2")
        add_interface(node4, create_interface("10.0.3.1"))
        node5 = create_node("node5", "10.0.3.2")
        add_interface(node5, create_interface("10.0.4.1"))
        node6 = create_node("node6", "10.0.4.2")

        add_node(node1)
        add_node(node2)
        add_node(node3)
        add_node(node4)
        add_node(node5)
        add_node(node6)

        add_connection(node1, node2, 0, 0)
        add_connection(node2, node3, 1, 0)
        add_connection(node3, node4, 1, 0)
        add_connection(node4, node5, 1, 0)
        add_connection(node5, node6, 1, 0)

        s1 = create_session("user1", [node1, node2, node3])
        s2 = create_session("user1", [node3, node4, node5], parent=s1)
        s3 = create_session("user1", [node5, node6], parent=s2)

        it = s3.forward_iterator
        self.assertTrue(it.has_next(), "Forward iterator has some elements")
        hop = next(it)
        self.assertEqual(hop.src.id, "node1", "Correct first iteration - source")
        self.assertEqual(hop.dst.id, "node2", "Correct first iteration - destination")
        next(it)
        hop = next(it)
        self.assertEqual(hop.src.id, "node3", "Correct parent jump - source")
        self.assertEqual(hop.dst.id, "node4", "Correct parent jump - destination")
        next(it)
        hop = next(it)
        self.assertEqual(hop.src.id, "node5", "Correct parent jump and path addition - source")
        self.assertEqual(hop.dst.id, "node6", "Correct parent jump and path addition - destination")
        self.assertFalse(it.has_next(), "Forward iterator has no elements left")
        with self.assertRaises(StopIteration):
            next(it)

        with self.assertRaises(Exception):
            create_session("user2", ["node6", "node7"], parent=s3)

        with self.assertRaises(Exception):
            create_session("user1", [node2, node3], parent=s1)

        it2 = s3.reverse_iterator
        self.assertTrue(it2.has_next(), "Reverse iterator has some elements")
        hop = next(it2)
        self.assertEqual(hop.src.id, "node6", "Correct first iteration - source")
        self.assertEqual(hop.dst.id, "node5", "Correct first iteration - destination")
        hop = next(it2)
        self.assertEqual(hop.src.id, "node5", "Correct parent jump - source")
        self.assertEqual(hop.dst.id, "node4", "Correct parent jump - destination")
        next(it2)
        hop = next(it2)
        self.assertEqual(hop.src.id, "node3", "Correct second parent jump - source")
        self.assertEqual(hop.dst.id, "node2", "Correct second parent jump - destination")
        next(it2)
        self.assertFalse(it2.has_next(), "Reverse iterator has no elements left")
        with self.assertRaises(StopIteration):
            next(it2)

        env.control.commit()

    def test_0002_message_traversal(self):
        # Scenario: we have an attacker node, two routers and three targets linked in this fashion: A-S1-S2-T1
        #                                                                                                   \T2
        #                                                                                                   \T3
        # The attacker establishes a session from A to T1 and from this session establishes another to T2 and
        # from this one sends a message to T3.
        # An entire environment must be constructed for this to test, because the environment shuffles around
        # messages.

        local_password_auth = AuthenticationProviderConfig \
                (
                provider_type=AuthenticationProviderType.LOCAL,
                token_type=AuthenticationTokenType.PASSWORD,
                token_security=AuthenticationTokenSecurity.SEALED,
                timeout=30
            )

        ssh_service = PassiveServiceConfig \
                (
                name="ssh",
                owner="ssh",
                version="8.0.0",
                local=False,
                access_level=AccessLevel.LIMITED,
                authentication_providers=["ssh_pwd_auth"],
                parameters=[
                    (ServiceParameter.ENABLE_SESSION, True),
                    (ServiceParameter.SESSION_ACCESS_LEVEL, AccessLevel.LIMITED)
                ],
                access_schemes=[AccessSchemeConfig(
                    authentication_providers=["ssh_pwd_auth"],
                    authorization_domain=AuthorizationDomainConfig(
                        type=AuthorizationDomainType.LOCAL,
                        authorizations=[
                            AuthorizationConfig("root", AccessLevel.ELEVATED)
                        ]
                    )
                )]
            )

        bash = PassiveServiceConfig(
            name="bash",
            owner="bash",
            version="5.0.0",
            local=True,
            access_level=AccessLevel.LIMITED,
            authentication_providers=["bash_login"],
            access_schemes=[AccessSchemeConfig(
                authentication_providers=["bash_login"],
                authorization_domain=AuthorizationDomainConfig(
                    type=AuthorizationDomainType.LOCAL,
                    authorizations=[
                        AuthorizationConfig("root", AccessLevel.ELEVATED)
                    ]
                )
            )]
        )

        target1 = NodeConfig(
            id="target1",
            active_services=[],
            passive_services=[
                PassiveServiceConfig \
                        (
                        name="ssh",
                        owner="ssh",
                        version="8.0.0",
                        local=False,
                        access_level=AccessLevel.LIMITED,
                        authentication_providers=[local_password_auth("t1_ssh_pwd_auth")],
                        parameters=[
                            (ServiceParameter.ENABLE_SESSION, True),
                            (ServiceParameter.SESSION_ACCESS_LEVEL, AccessLevel.LIMITED)
                        ],
                        access_schemes=[AccessSchemeConfig(
                            authentication_providers=["t1_ssh_pwd_auth"],
                            authorization_domain=AuthorizationDomainConfig(
                                type=AuthorizationDomainType.LOCAL,
                                authorizations=[
                                    AuthorizationConfig("root", AccessLevel.ELEVATED)
                                ]
                            )
                        )]
                    ),

                PassiveServiceConfig(
                    name="bash",
                    owner="bash",
                    version="5.0.0",
                    local=True,
                    access_level=AccessLevel.LIMITED,
                    authentication_providers=[local_password_auth("t1_bash_login")],
                    access_schemes=[AccessSchemeConfig(
                        authentication_providers=["t1_bash_login"],
                        authorization_domain=AuthorizationDomainConfig(
                            type=AuthorizationDomainType.LOCAL,
                            authorizations=[
                                AuthorizationConfig("root", AccessLevel.ELEVATED)
                            ]
                        )
                    )]
                )

            ],
            traffic_processors=[],
            shell="bash",
            interfaces=[InterfaceConfig(IPAddress("192.168.1.2"), IPNetwork("192.168.1.0/24")),
                        InterfaceConfig(IPAddress("192.168.2.2"), IPNetwork("192.168.2.0/24"))]
        )

        target2 = NodeConfig(
            id="target2",
            active_services=[],
            passive_services=[
                PassiveServiceConfig \
                        (
                        name="ssh",
                        owner="ssh",
                        version="8.0.0",
                        local=False,
                        access_level=AccessLevel.LIMITED,
                        authentication_providers=[local_password_auth("t2_ssh_pwd_auth")],
                        parameters=[
                            (ServiceParameter.ENABLE_SESSION, True),
                            (ServiceParameter.SESSION_ACCESS_LEVEL, AccessLevel.LIMITED)
                        ],
                        access_schemes=[AccessSchemeConfig(
                            authentication_providers=["t2_ssh_pwd_auth"],
                            authorization_domain=AuthorizationDomainConfig(
                                type=AuthorizationDomainType.LOCAL,
                                authorizations=[
                                    AuthorizationConfig("root", AccessLevel.ELEVATED)
                                ]
                            )
                        )]
                    ),

                PassiveServiceConfig(
                    name="bash",
                    owner="bash",
                    version="5.0.0",
                    local=True,
                    access_level=AccessLevel.LIMITED,
                    authentication_providers=[local_password_auth("t2_bash_login")],
                    access_schemes=[AccessSchemeConfig(
                        authentication_providers=["t2_bash_login"],
                        authorization_domain=AuthorizationDomainConfig(
                            type=AuthorizationDomainType.LOCAL,
                            authorizations=[
                                AuthorizationConfig("root", AccessLevel.ELEVATED)
                            ]
                        )
                    )]
                )
            ],
            traffic_processors=[],
            shell="bash",
            interfaces=[InterfaceConfig(IPAddress("192.168.2.3"), IPNetwork("192.168.2.0/24")),
                        InterfaceConfig(IPAddress("192.168.3.3"), IPNetwork("192.168.3.0/24"))]
        )

        target3 = NodeConfig(
            id="target3",
            active_services=[],
            passive_services=[
                PassiveServiceConfig \
                        (
                        name="ssh",
                        owner="ssh",
                        version="8.0.0",
                        local=False,
                        access_level=AccessLevel.LIMITED,
                        authentication_providers=[local_password_auth("t3_ssh_pwd_auth")],
                        parameters=[
                            (ServiceParameter.ENABLE_SESSION, True),
                            (ServiceParameter.SESSION_ACCESS_LEVEL, AccessLevel.LIMITED)
                        ],
                        access_schemes=[AccessSchemeConfig(
                            authentication_providers=["t3_ssh_pwd_auth"],
                            authorization_domain=AuthorizationDomainConfig(
                                type=AuthorizationDomainType.LOCAL,
                                authorizations=[
                                    AuthorizationConfig("root", AccessLevel.ELEVATED)
                                ]
                            )
                        )]
                    ),

                PassiveServiceConfig(
                    name="bash",
                    owner="bash",
                    version="5.0.0",
                    local=True,
                    access_level=AccessLevel.LIMITED,
                    authentication_providers=[local_password_auth("t3_bash_login")],
                    access_schemes=[AccessSchemeConfig(
                        authentication_providers=["t3_bash_login"],
                        authorization_domain=AuthorizationDomainConfig(
                            type=AuthorizationDomainType.LOCAL,
                            authorizations=[
                                AuthorizationConfig("root", AccessLevel.ELEVATED)
                            ]
                        )
                    )]
                )
            ],
            traffic_processors=[],
            shell="bash",
            interfaces=[InterfaceConfig(IPAddress("192.168.3.4"), IPNetwork("192.168.3.0/24"))]
        )

        attacker_node = NodeConfig(
            active_services=[
                ActiveServiceConfig(
                    type="scripted_actor",
                    name="scripted_actor",
                    owner="attacker",
                    access_level=AccessLevel.LIMITED,
                )
            ],
            passive_services=[],
            traffic_processors=[],
            interfaces=[
                InterfaceConfig(IPAddress("192.168.0.2"), IPNetwork("192.168.0.0/24"))
            ],
            shell="",
            name="attacker_node"
        )

        router1 = RouterConfig(
            traffic_processors=[
                FirewallConfig(
                    default_policy=FirewallPolicy.DENY,
                    chains=[
                        FirewallChainConfig(
                            type=FirewallChainType.FORWARD,
                            policy=FirewallPolicy.DENY,
                            rules=[
                                FirewallRule(IPNetwork("192.168.0.0/24"), IPNetwork("192.168.0.0/24"), "*", FirewallPolicy.ALLOW),
                                FirewallRule(IPNetwork("192.168.1.0/24"), IPNetwork("192.168.0.0/24"), "*", FirewallPolicy.ALLOW)
                            ]
                        )
                    ]
                )
            ],
            interfaces=[
                InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.0/24"), index=0),
                InterfaceConfig(IPAddress("10.0.0.1"), IPNetwork("10.0.0.0/24"), index=1)
            ],
            routing_table=[
                RouteConfig(
                    network=IPNetwork("192.168.1.0/255.255.255.0"),
                    port=1
                ),
                RouteConfig(
                    network=IPNetwork("192.168.2.0/255.255.255.0"),
                    port=1
                )
            ],
            name="router1"
        )

        router2 = RouterConfig(
            traffic_processors=[
                FirewallConfig(
                    default_policy=FirewallPolicy.DENY,
                    chains=[
                        FirewallChainConfig(
                            type=FirewallChainType.FORWARD,
                            policy=FirewallPolicy.DENY,
                            rules=[
                                FirewallRule(IPNetwork("192.168.0.0/24"), IPNetwork("192.168.1.0/24"), "*", FirewallPolicy.ALLOW),
                                FirewallRule(IPNetwork("192.168.1.0/24"), IPNetwork("192.168.1.0/24"), "*", FirewallPolicy.ALLOW),
                                FirewallRule(IPNetwork("192.168.2.0/24"), IPNetwork("192.168.2.0/24"), "*", FirewallPolicy.ALLOW),
                                FirewallRule(IPNetwork("192.168.3.0/24"), IPNetwork("192.168.3.0/24"), "*", FirewallPolicy.ALLOW)
                            ]
                        )
                    ]
                )
            ],
            interfaces=[
                InterfaceConfig(IPAddress("192.168.1.1"), IPNetwork("192.168.1.0/24"), index=0),
                InterfaceConfig(IPAddress("192.168.2.1"), IPNetwork("192.168.2.0/24"), index=1),
                InterfaceConfig(IPAddress("192.168.3.1"), IPNetwork("192.168.3.0/24"), index=2),
                InterfaceConfig(IPAddress("10.0.0.2"), IPNetwork("10.0.0.0/24"), index=3)
            ],
            routing_table=[
                RouteConfig(
                    network=IPNetwork("192.168.0.0/255.255.255.0"),
                    port=3
                )
            ],
            name="router2"
        )

        connections = [
            ConnectionConfig(router1, 1, router2, 3),
            ConnectionConfig(attacker_node, 0, router1, 0),
            ConnectionConfig(target1, 0, router2, 0),
            ConnectionConfig(target1, 1, router2, 1),
            ConnectionConfig(target2, 0, router2, 1),
            ConnectionConfig(target2, 1, router2, 2),
            ConnectionConfig(target3, 0, router2, 2)
        ]

        env = Environment.create().configure(target1, target2, target3, attacker_node, router1, router2, *connections)
        env.control.add_pause_on_response("attacker_node.scripted_actor")

        # This is ugly but serves its purpose, until the authentication/authorization framework is more fleshed out
        ssh_token_t1 = env.configuration.access.create_authentication_token(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, "root", True)._set_content(uuid.uuid4())
        ssh_token_t2 = env.configuration.access.create_authentication_token(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, "root", True)._set_content(uuid.uuid4())
        ssh_token_t3 = env.configuration.access.create_authentication_token(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, "root", True)._set_content(uuid.uuid4())

        create_session = env.configuration.network.create_session

        # Create a simple scripted attacker
        attacker = env.configuration.service.get_service_interface(
            env.configuration.general.get_object_by_id("attacker_node.scripted_actor", Service).active_service,
            ScriptedActorControl)

        router1 = env.configuration.general.get_object_by_id("router1", Node)
        router2 = env.configuration.general.get_object_by_id("router2", Node)

        assert None not in [router1, router2]

        env.configuration.node.add_routing_rule(router1,
                                                FirewallRule(IPNetwork("192.168.1.0/24"), IPNetwork("192.168.0.0/24"),
                                                             "*", FirewallPolicy.ALLOW))
        env.configuration.node.add_routing_rule(router2,
                                                FirewallRule(IPNetwork("192.168.0.0/24"), IPNetwork("192.168.1.0/24"),
                                                             "*", FirewallPolicy.ALLOW))

        env.control.init()

        # Get correct actions
        actions = {}
        action_list = env.resources.action_store.get_prefixed("cyst")
        for action in action_list:
            actions[action.id] = action

        action = actions["cyst:network:create_session"]

        # Test direct connection to an inaccessible node
        attacker.execute_action("192.168.2.2", "ssh", action, session=None, auth=ssh_token_t1)

        env.control.run()

        response = attacker.get_last_response()
        s = response.session

        self.assertEqual(response.status.origin, StatusOrigin.NETWORK, "Got response from network")
        self.assertEqual(response.status.value, StatusValue.FAILURE, "host unreachable")

        # Correct via multiple sessions

        attacker.execute_action("192.168.1.2", "ssh", action, session=None, auth=ssh_token_t1)

        env.control.run()

        response = attacker.get_last_response()
        s = response.session

        self.assertTrue(response.session, "Received a session back")

        # session1 = SessionImpl("root", None, path=[Hop(Endpoint(id='attacker_node', port=0), Endpoint(id='router1', port=1)), Hop(Endpoint(id='router1', port=0), Endpoint(id='router2', port=0)), Hop(Endpoint(id='router2', port=1), Endpoint(id='target1', port=0))])
        session1 = create_session("root", ["attacker_node", "router1", "router2", "target1"],
                                  src_service="scripted_actor", dst_service="ssh")
        self.assertEqual(s, session1)

        attacker.execute_action("192.168.2.3", "ssh", action, session=s, auth=ssh_token_t2)

        env.control.run()

        response = attacker.get_last_response()
        s = response.session

        self.assertTrue(response.session, "Received a session back")

        # session2 = SessionImpl("root", session1, path=[Hop(src=Endpoint(id='target1', port=1), dst=Endpoint(id='router2', port=2)), Hop(src=Endpoint(id='router2', port=3), dst=Endpoint(id='target2', port=0))])
        # TODO: handle nested creation of session with specified source/destination
        # session2 = create_session("root", ["target1", "router2", "target2"], parent=session1)
        # self.assertEqual(s, session2)

        # Now to just try running an action over two sessions
        action = actions["cyst:host:get_services"]
        attacker.execute_action("192.168.3.4", "ssh", action, session=s, auth=ssh_token_t3)

        env.control.run()

        response = attacker.get_last_response()
        self.assertEqual([item[0] for item in response.content], ["ssh", "bash"])

        env.control.commit()

    def test_0003_active_service_opened_sessions(self):

        active_node_1 = NodeConfig(
            active_services=[
                ActiveServiceConfig(
                    type="scripted_actor",
                    name="scripted_actor",
                    owner="actor_1",
                    access_level=AccessLevel.LIMITED,
                )
            ],
            passive_services=[],
            traffic_processors=[],
            shell="",
            interfaces=[
                InterfaceConfig(IPAddress("192.168.0.2"), IPNetwork("192.168.0.2/24"))
            ],
            name="active_node_1"
        )

        active_node_2 = NodeConfig(
            active_services=[
                ActiveServiceConfig(
                    type="scripted_actor",
                    name="scripted_actor",
                    owner="actor_2",
                    access_level=AccessLevel.LIMITED,
                )
            ],
            passive_services=[],
            traffic_processors=[],
            shell="",
            interfaces=[
                InterfaceConfig(IPAddress("192.168.0.3"), IPNetwork("192.168.0.3/24")),
                InterfaceConfig(IPAddress("192.168.1.2"), IPNetwork("192.168.1.2/24"))
            ],
            name="active_node_2"
        )

        passive_node = NodeConfig(
            active_services=[],
            passive_services=[],
            traffic_processors=[],
            shell="",
            interfaces=[
                InterfaceConfig(IPAddress("192.168.1.3"), IPNetwork("192.168.1.3/24"))
            ],
            name="passive_node"
        )

        router = RouterConfig(
            traffic_processors=[
                FirewallConfig(
                    default_policy=FirewallPolicy.DENY,
                    chains=[
                        FirewallChainConfig(
                            type=FirewallChainType.FORWARD,
                            policy=FirewallPolicy.DENY,
                            rules=[
                                FirewallRule(src_net=IPNetwork("192.168.0.1/24"), dst_net=IPNetwork("192.168.0.1/24"), service="*", policy=FirewallPolicy.ALLOW),
                                FirewallRule(src_net=IPNetwork("192.168.1.1/24"), dst_net=IPNetwork("192.168.1.1/24"), service="*", policy=FirewallPolicy.ALLOW)
                            ]
                        )
                    ]
                )
            ],
            interfaces=[
                InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.0/24"), index=0),
                InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.0/24"), index=1),
                InterfaceConfig(IPAddress("192.168.1.1"), IPNetwork("192.168.1.0/24"), index=2),
                InterfaceConfig(IPAddress("192.168.1.1"), IPNetwork("192.168.1.0/24"), index=3)
            ],
            routing_table=[],
            name="router"
        )

        connections = [
            ConnectionConfig(active_node_1, 0, router, 0),
            ConnectionConfig(active_node_2, 0, router, 1),
            ConnectionConfig(active_node_2, 1, router, 2),
            ConnectionConfig(passive_node,  0, router, 3)
        ]

        env = Environment.create().configure(active_node_1, active_node_2, passive_node, router, *connections)
        env.control.init()

        env.control.add_pause_on_response("active_node_1.scripted_actor")

        actor1 = env.configuration.service.get_service_interface(
            env.configuration.general.get_object_by_id("active_node_1.scripted_actor", Service).active_service,
            ScriptedActorControl)

        actor2 = env.configuration.service.get_service_interface(
            env.configuration.general.get_object_by_id("active_node_2.scripted_actor", Service).active_service,
            ScriptedActorControl)

        # A function to open a session as a reaction to an incoming request
        def open_session_and_respond(messaging: EnvironmentMessaging, resources: EnvironmentResources, message: Message) -> Tuple[bool, int]:
            request = message.cast_to(Request)
            session = messaging.open_session(request)
            res = messaging.create_response(request, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), session=session)
            messaging.send_message(res)
            return True, 1

        actor2.set_request_callback(open_session_and_respond)

        # --------------------------------------------------------------------------------------------------------------
        # Testing of opening of sessions upon an incoming request
        # - actor_1 tries to connect to passive_node (unsuccessfully)
        # - actor_1 connects to actor_2 and actor_2 opens a session
        # - actor_1 use the session to connect to the passive_node

        # - actor_1 tries to connect to passive_node (unsuccessfully)
        action1 = env.resources.action_store.get("cyst:test:echo_success")
        actor1.execute_action("192.168.1.3", "", action1)

        env.control.run()
        response = actor1.get_last_response()
        self.assertTrue(response.status == Status(StatusOrigin.NETWORK, StatusValue.FAILURE), f"Failed to connect the passive service in different network. Reason: {str(response)}")

        # - actor_1 connects to actor_2 and actor_2 opens a session
        action2 = env.resources.action_store.get("cyst:active_service:action_1")
        actor1.execute_action("192.168.0.3", "scripted_actor", action2)

        env.control.run()
        response = actor1.get_last_response()
        self.assertTrue(response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), f"Failed to connect with active service to get a session. Reason: {str(response)}")

        # - actor_1 use the session to connect to the passive_node
        session = response.session
        actor1.execute_action("192.168.1.3", "", action1, session=session)

        env.control.run()
        response = actor1.get_last_response()
        self.assertTrue(response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), f"Selected session could not be used to connect the passive service. Reason: {str(response)}")

        env.control.commit()

    def test_0004_test_session_configuration(self):
        active_node_1 = NodeConfig(
            active_services=[
                ActiveServiceConfig(
                    type="scripted_actor",
                    name="scripted_actor",
                    owner="actor_1",
                    access_level=AccessLevel.LIMITED,
                )
            ],
            passive_services=[],
            traffic_processors=[],
            shell="",
            interfaces=[
                InterfaceConfig(IPAddress("192.168.0.2"), IPNetwork("192.168.0.2/24"))
            ],
            name="active_node_1"
        )

        passive_service = PassiveServiceConfig(
            name="random_service",
            owner="random_service",
            version="1.2.3",
            local=False,
            access_level=AccessLevel.LIMITED
        )

        passive_node_1 = NodeConfig(
            active_services=[],
            passive_services=[passive_service()],
            traffic_processors=[],
            shell="",
            interfaces=[
                InterfaceConfig(IPAddress("192.168.1.2"), IPNetwork("192.168.1.2/24"))
            ],
            name="passive_node_1"
        )

        passive_node_2 = NodeConfig(
            active_services=[],
            passive_services=[passive_service()],
            traffic_processors=[],
            shell="",
            interfaces=[
                InterfaceConfig(IPAddress("192.168.1.3"), IPNetwork("192.168.1.3/24"))
            ],
            name="passive_node_2"
        )

        router = RouterConfig(
            traffic_processors=[
                FirewallConfig(
                    default_policy=FirewallPolicy.DENY,
                    chains=[
                        FirewallChainConfig(
                            type=FirewallChainType.FORWARD,
                            policy=FirewallPolicy.DENY,
                            rules=[
                                # Inter-network connections
                                FirewallRule(src_net=IPNetwork("192.168.0.1/24"), dst_net=IPNetwork("192.168.0.1/24"), service="*", policy=FirewallPolicy.ALLOW),
                                FirewallRule(src_net=IPNetwork("192.168.1.1/24"), dst_net=IPNetwork("192.168.1.1/24"), service="*", policy=FirewallPolicy.ALLOW),
                                # Connection from inside network outside
                                FirewallRule(src_net=IPNetwork("192.168.1.1/24"), dst_net=IPNetwork("192.168.0.1/24"), service="*", policy=FirewallPolicy.ALLOW)
                            ]
                        )
                    ]
                )
            ],
            interfaces=[
                InterfaceConfig(IPAddress("192.168.0.1"), IPNetwork("192.168.0.0/24"), index=0),
                InterfaceConfig(IPAddress("192.168.1.1"), IPNetwork("192.168.1.0/24"), index=1),
                InterfaceConfig(IPAddress("192.168.1.1"), IPNetwork("192.168.1.0/24"), index=2)
            ],
            routing_table=[],
            name="router"
        )

        connections = [
            ConnectionConfig(active_node_1, 0, router, 0),
            ConnectionConfig(passive_node_1, 0, router, 1),
            ConnectionConfig(passive_node_2, 0, router, 2)
        ]

        sessions = [
            SessionConfig(src_service="scripted_actor", dst_service="random_service", waypoints=["active_node_1", "router", "passive_node_1"], reverse=True, id="session_1")
        ]

        all_config = [active_node_1, passive_node_1, passive_node_2, router, *connections, *sessions]

        env = Environment.create().configure(*all_config)
        env.control.init()

        env.control.add_pause_on_response("active_node_1.scripted_actor")

        actor1 = env.configuration.service.get_service_interface(
            env.configuration.general.get_object_by_id("active_node_1.scripted_actor", ActiveService),
            ScriptedActorControl)

        actor1.execute_action("192.168.1.3", "random_service", env.resources.action_store.get("cyst:test:echo_success"), "session_1")
        env.control.run()

        response = actor1.get_last_response()

        # TODO: So far, we are considering only the happy path
        self.assertTrue(response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS))

        env.control.commit()


class TestRouting(unittest.TestCase):

    def test_0000_routing(self):
        env = Environment.create()
        env.control.init()

        add_route = env.configuration.node.add_route

        router1 = env.configuration.node.create_router("router1", env.messaging)
        router1_port = env.configuration.node.add_interface(router1, env.configuration.node.create_interface("10.0.0.0",
                                                                                                             "255.255.0.0"))

        # Technically, the last route is all tha is needed, but this is to test overlapping and correct ordering
        add_route(router1, Route(IPNetwork("10.1.0.0/30"), router1_port))
        add_route(router1, Route(IPNetwork("10.1.0.0/26"), router1_port, metric=30))
        add_route(router1, Route(IPNetwork("10.1.0.0/22"), router1_port))
        add_route(router1, Route(IPNetwork("10.1.0.0/16"), router1_port))
        add_route(router1, Route(IPNetwork("10.1.5.4/16"), router1_port))
        add_route(router1, Route(IPNetwork("10.1.5.4/16"), router1_port))

        routes = env.configuration.node.list_routes(router1)
        self.assertEqual(routes[0].net.prefixlen, 26, "Correctly prioritized metric")
        self.assertEqual(routes[1].net.prefixlen, 30, "Correctly prioritized prefixlen")
        self.assertEqual(routes[5].net.ip, IPAddress("10.1.5.4"), "Correctly ordered IP addresses")

    def test_0001_cycle(self):
        env = Environment.create()
        env.control.init()
        env.control.add_pause_on_response("attacker_node.scripted_actor")

        # Function aliases to make it more readable
        create_node = env.configuration.node.create_node
        create_router = env.configuration.node.create_router
        create_active_service = env.configuration.service.create_active_service
        add_service = env.configuration.node.add_service
        create_interface = env.configuration.node.create_interface
        add_node = env.configuration.network.add_node
        add_connection = env.configuration.network.add_connection
        add_route = env.configuration.node.add_route
        add_interface = env.configuration.node.add_interface

        # Router connected to attacker and router2
        router1 = create_router("router1", env.messaging)
        # attacker-facing port
        router1_port1 = add_interface(router1, create_interface("10.0.0.1", "255.255.0.0"))
        # router2-facing port
        router1_port2 = add_interface(router1, create_interface())

        # Router connected only to router1
        router2 = create_router("router2", env.messaging)
        # router1-facing port
        router2_port1 = add_interface(router2, create_interface())

        # Make an endless routing loop
        add_route(router1, Route(IPNetwork("192.168.0.0/24"), router1_port2))
        add_route(router2, Route(IPNetwork("192.168.0.0/24"), router2_port1))
        add_route(router2, Route(IPNetwork("10.0.0.0/8"), router2_port1))

        # Connect routers
        add_node(router1)
        add_node(router2)
        add_connection(router1, router2, router1_port2, router2_port1)

        # attacker sending the message
        attacker_node = create_node("attacker_node")
        attacker_service = create_active_service("scripted_actor", "attacker", "scripted_actor", attacker_node)
        add_service(attacker_node, attacker_service)
        attacker = ScriptedActor.cast_from(attacker_service)

        # Connect attacker
        add_node(attacker_node)
        add_connection(attacker_node, router1, -1, router1_port1)

        # Let attacker send a probe message
        action = env.resources.action_store.get("cyst:test:echo_success")

        attacker.execute_action("192.168.0.2", "", action)

        env.control.run()

        response = attacker.get_last_response()

        self.assertEqual(response.status, Status(StatusOrigin.NETWORK, StatusValue.FAILURE), "Network failure occurred")
        self.assertEqual(response.content, "Message stuck in a cycle")

    def test_0002_ttl(self):
        env = Environment.create()
        env.control.init()
        env.control.add_pause_on_response("attacker_node.scripted_actor")

        # Function aliases to make it more readable
        create_node = env.configuration.node.create_node
        create_router = env.configuration.node.create_router
        create_active_service = env.configuration.service.create_active_service
        add_service = env.configuration.node.add_service
        create_interface = env.configuration.node.create_interface
        add_node = env.configuration.network.add_node
        add_connection = env.configuration.network.add_connection
        add_route = env.configuration.node.add_route
        add_interface = env.configuration.node.add_interface

        # Router connected to attacker and router2
        router1 = create_router("router1", env.messaging)
        # attacker-facing port
        router1_port1 = add_interface(router1, create_interface("10.0.0.1", "255.255.0.0"))
        # router2-facing port
        router1_port2 = add_interface(router1, create_interface())

        add_node(router1)

        last_router = router1
        # Make a chain of 70 routers
        for i in range(2, 70):
            router = create_router("router{}".format(i), env.messaging)
            add_interface(router, create_interface())  # port 0
            add_interface(router, create_interface())  # port 1

            add_node(router)
            add_connection(last_router, router, 1, 0)

            add_route(last_router, Route(IPNetwork("192.168.0.0/16"), 1))
            last_router = router

        # attacker
        attacker_node = create_node("attacker_node")
        attacker_service = create_active_service("scripted_actor", "attacker", "scripted_actor", attacker_node)
        add_service(attacker_node, attacker_service)
        attacker = ScriptedActor.cast_from(attacker_service)

        # Connect attacker
        add_node(attacker_node)
        add_connection(attacker_node, router1, -1, router1_port1)

        # Let attacker send a probe message
        action = env.resources.action_store.get("cyst:test:echo_success")

        attacker.execute_action("192.168.0.2", "", action)

        env.control.run()

        response = attacker.get_last_response()

        self.assertEqual(response.status, Status(StatusOrigin.NETWORK, StatusValue.FAILURE), "Network failure occurred")
        self.assertEqual(response.content, "TTL expired")


class TestService(unittest.TestCase):

    def test_000_service_removal(self):
        env = Environment.create()

        # Function aliases to make it more readable
        create_passive_service = env.configuration.service.create_passive_service
        create_node = env.configuration.node.create_node
        add_service = env.configuration.node.add_service
        remove_service = env.configuration.node.remove_service

        # Create two services and a node which will house them
        service1 = create_passive_service("service1", "service1")
        service2 = create_passive_service("service2", "service2")

        node = create_node("node")
        add_service(node, service1, service2)

        self.assertDictEqual(node.services, {"service1": service1, "service2": service2}, "Services added")

        # Remove services one by one
        remove_service(node, service2)
        self.assertDictEqual(node.services, {"service1": service1}, "Removed last service")

        remove_service(node, service1)
        self.assertDictEqual(node.services, {}, "Removed both services")

        # No services left, silently do nothing
        remove_service(node, service1, service2)
        self.assertDictEqual(node.services, {}, "Both services still removed")


class TestConnection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.SOURCE = "192.168.0.2"
        source_node = NodeConfig(
            active_services=[
                ActiveServiceConfig(
                    type="scripted_actor",
                    name="attacker",
                    owner="scripted_actor",
                    access_level=AccessLevel.ELEVATED,
                )
            ],
            passive_services=[],
            traffic_processors=[],
            shell="",
            interfaces=[InterfaceConfig(IPAddress(cls.SOURCE), IPNetwork("192.168.0.2/24"))],
            name="source_node"
        )

        cls.DESTINATION = "192.168.0.3"
        destination_node = NodeConfig(
            active_services=[],
            passive_services=[],
            traffic_processors=[],
            shell="",
            interfaces=[InterfaceConfig(IPAddress(cls.DESTINATION), IPNetwork("192.168.0.3/24"))],
            name="destination_node"
        )

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
            name="router"
        )

        connections = [
                ConnectionConfig(source_node, 0, router, 0),
                ConnectionConfig(destination_node, 0, router, 1),
        ]

        cls.configs = [source_node, destination_node, router, *connections]

    def setUp(self) -> None:
        self.env = Environment.create().configure(*self.configs)
        self.env.control.init()
        self.source_node = self.env.platform.configuration.general.get_object_by_id("source_node", Node)
        self.destination_node = self.env.configuration.general.get_object_by_id("destination_node", Node)
        self.attacker = self.env.configuration.service.get_service_interface(
            self.env.infrastructure.service_store.get_active_service("source_node.attacker"),
            ScriptedActorControl)

    def test_0000_init(self) -> None:
        self.assertNotIn(None, [self.env, self.source_node, self.destination_node, self.attacker],
                         "Environment and nodes initialized")
        self.assertEqual(self.source_node.interfaces[0].ip, IPAddress(self.SOURCE),
                         "Source node's interface IP set correctly")
        self.assertEqual(self.destination_node.interfaces[0].ip, IPAddress(self.DESTINATION),
                         "Destination node's interface IP set correctly")

    def test_0001_get_connections(self) -> None:
        connections = self.env.configuration.network.get_connections(self.source_node)
        self.assertEqual(len(connections), 1, "Got the correct number of connections")
        self.assertEqual(connections[0], self.source_node.interfaces[0].connection, "Got the correct connection")
        self.assertFalse(connections[0].blocked, "Connection is initialized as not blocked")
        self.assertEqual(connections[0].delay, 0, "Connection's delay is initialized to 0")

    def test_0002_set_params(self) -> None:
        connection = self.env.configuration.network.get_connections(self.destination_node)[0]
        connection.set_params(delay=10, blocked=True)
        self.assertEqual(connection.delay, 10, "Delay set to 10")
        self.assertTrue(connection.blocked, "Connection set to blocked")

    def test_0003_delay(self) -> None:
        connection = self.env.configuration.network.get_connections(self.destination_node)[0]
        connection.set_params(delay=10)
        action = self.env.resources.action_store.get("cyst:test:echo_success")
        assert action

        self.attacker.execute_action(self.DESTINATION, "", action)
        self.env.control.run()
        # Request is delayed by 10 units and it's response by another 10
        self.assertGreaterEqual(self.env.resources.clock.current_time(), 20, "Time moved by 20 seconds")

    def test_0004_block(self) -> None:
        # TODO: Blocking of connection is not yet implemented
        pass


if __name__ == '__main__':
    unittest.main()
