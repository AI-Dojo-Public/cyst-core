import unittest
from cyst.api.configuration import *
from cyst.api.environment.environment import Environment

class TestParametrization(unittest.TestCase):
    def setUp(self):
        self.target = NodeConfig(
            active_services=[],
            passive_services=[
                PassiveServiceConfig(
                    name="bash",
                    owner="root",
                    version=ConfigParameter("my-custom-version"),
                    access_level=ConfigParameter("my-custom-access-level"),
                    local=True,
                ),
                PassiveServiceConfig(
                    name="lighttpd",
                    owner="www",
                    version="1.4.62",
                    access_level=AccessLevel.LIMITED,
                    local=False,
                )
            ],
            shell="bash",
            traffic_processors=[],
            interfaces=[],
            name="target"
        )

        self.attacker_service = ActiveServiceConfig(
            type="scripted_actor",
            name="attacker",
            owner="attacker",
            access_level=AccessLevel.LIMITED,
            ref="attacker_service_ref"
        )

        self.test_firewall = ActiveServiceConfig(
            type="firewall",
            name="test_firewall",
            owner="root",
            access_level=AccessLevel.LIMITED,
            ref="test_firewall_ref"
        )

        self.attacker_node_1 = NodeConfig(
            active_services=[ConfigParameter("attacker_location_1"), ConfigParameter("test_firewall_location_1")],
            passive_services=[],
            interfaces=[],
            shell="",
            traffic_processors=[],
            name="attacker_node_1"
        )

        self.attacker_node_2 = NodeConfig(
            active_services=[ConfigParameter("attacker_location_2"), ConfigParameter("test_firewall_location_2")],
            passive_services=[],
            interfaces=[],
            shell="",
            traffic_processors=[],
            name="attacker_node_2"
        )

        self.router = RouterConfig(
            interfaces=[
                InterfaceConfig(
                    ip=IPAddress("192.168.0.1"),
                    net=IPNetwork("192.168.0.1/24"),
                    index=0
                ),
                InterfaceConfig(
                    ip=IPAddress("192.168.0.1"),
                    net=IPNetwork("192.168.0.1/24"),
                    index=1
                ),
                InterfaceConfig(
                    ip=IPAddress("192.168.0.1"),
                    net=IPNetwork("192.168.0.1/24"),
                    index=2
                )
            ],
            traffic_processors=[
                FirewallConfig(
                    default_policy=FirewallPolicy.ALLOW,
                    chains=[
                        FirewallChainConfig(
                            type=FirewallChainType.FORWARD,
                            policy=FirewallPolicy.ALLOW,
                            rules=[]
                        )
                    ]
                )
            ],
            id="router"
        )

        self.exploit1 = ExploitConfig(
            services=[
                VulnerableServiceConfig(
                    service="lighttpd",
                    min_version="1.3.11",
                    max_version="1.4.62"
                )
            ],
            locality=ExploitLocality.REMOTE,
            category=ExploitCategory.CODE_EXECUTION,
            id="http_exploit"
        )

        self.connection1 = ConnectionConfig(
            src_ref=self.target.ref,
            src_port=-1,
            dst_ref=self.router.ref,
            dst_port=0
        )

        self.connection2 = ConnectionConfig(
            src_ref=self.attacker_node_1.ref,
            src_port=-1,
            dst_ref=self.router.ref,
            dst_port=1
        )

        self.connection3 = ConnectionConfig(
            src_ref=self.attacker_node_2.ref,
            src_port=-1,
            dst_ref=self.router.ref,
            dst_port=2
        )

        self.parametrization = ConfigParametrization(
            parameters=[
                ConfigParameterSingle(
                    name="Vulnerable service version",
                    value_type=ConfigParameterValueType.VALUE,
                    description="Sets the version of a vulnerable service. If you put version smaller than 1.3.11 and larger than 1.4.62, the exploit will not work.",
                    default="1.4.62",
                    parameter_id="my-custom-version"
                ),
                ConfigParameterSingle(
                    name="Vulnerable access level",
                    value_type=ConfigParameterValueType.VALUE,
                    description="Sets the access level for the service",
                    default="user",
                    parameter_id="my-custom-access-level"
                ),
                ConfigParameterGroup(
                    parameter_id="attacker-position",
                    name="Attacker position",
                    group_type=ConfigParameterGroupType.ONE,
                    value_type=ConfigParameterValueType.REF,
                    description="The node, where the attacker starts at.",
                    default=["attacker_location_1"],
                    options=[
                        ConfigParameterGroupEntry(
                            parameter_id="attacker_location_1",
                            value="attacker_service_ref",
                            description="Node 1"
                        ),
                        ConfigParameterGroupEntry(
                            parameter_id="attacker_location_2",
                            value="attacker_service_ref",
                            description="Node 2"
                        )
                    ]
                ),
                ConfigParameterGroup(
                    parameter_id="test-service-position",
                    name="Test service position",
                    group_type=ConfigParameterGroupType.ANY,
                    value_type=ConfigParameterValueType.REF,
                    description="The node, where to place testing service.",
                    default=["test_firewall_location_1", "test_firewall_location_2"],
                    options=[
                        ConfigParameterGroupEntry(
                            parameter_id="test_firewall_location_1",
                            value="test_firewall_ref",
                            description="Node 1"
                        ),
                        ConfigParameterGroupEntry(
                            parameter_id="test_firewall_location_2",
                            value="test_firewall_ref",
                            description="Node 2"
                        )
                    ]
                )
            ]
        )

        self.all_config = [
            self.target, self.test_firewall, self.attacker_service,
            self.attacker_node_1, self.attacker_node_2, self.router,
            self.exploit1, self.connection1, self.connection2, self.connection3,
            self.parametrization
        ]

        self.parameters = {
            "single_parameters": {
                "my-custom-access-level": "test_access_level",
                "my-custom-version": "1.4.62"
            },
            "group_parameters": {
                "attacker-position": ["attacker_location_1"]
            }
        }

    def test_parameters_in_config_items(self):
        e = Environment.create()
        e.configure(*self.all_config, parameters=self.parameters)
        e.control.init()
        e.control.commit()
        print(e.configuration.general.save_configuration(indent=4))

        for passive_service in self.target.passive_services:
            if passive_service.name == 'bash':
                self.assertEqual(passive_service.version, '1.4.62')
                self.assertEqual(passive_service.access_level, 'test_access_level')

        # Check that the correct services are assigned to the attacker nodes
        self.assertIn(self.attacker_service, self.attacker_node_1.active_services)
        self.assertIn(self.test_firewall, self.attacker_node_1.active_services)
        self.assertIn(self.test_firewall, self.attacker_node_2.active_services)
