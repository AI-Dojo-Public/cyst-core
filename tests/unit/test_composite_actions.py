import asyncio
import unittest
from typing import Tuple, Callable, Union, List, Coroutine, Any

from netaddr import IPNetwork, IPAddress

from cyst.api.configuration import NodeConfig, PassiveServiceConfig, AccessLevel, ExploitConfig, VulnerableServiceConfig, \
    ActiveServiceConfig, RouterConfig, InterfaceConfig, ConnectionConfig, FirewallConfig, FirewallChainConfig
from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.environment import Environment
from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue, MessageType
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.platform_specification import PlatformType, PlatformSpecification
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.host.service import Service
from cyst.api.logic.action import ActionDescription, ActionType, ActionParameter, ActionParameterType, Action
from cyst.api.logic.behavioral_model import BehavioralModel
from cyst.api.logic.composite_action import CompositeActionManager
from cyst.api.logic.exploit import ExploitLocality, ExploitCategory
from cyst.api.network.firewall import FirewallPolicy, FirewallChainType
from cyst.api.network.node import Node

from cyst_services.scripted_actor.main import ScriptedActorControl


# ----------------------------------------------------------------------------------------------------------------------
# A test behavioral model
# ----------------------------------------------------------------------------------------------------------------------
class CAMModel(BehavioralModel):
    def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                 composite_action_manager: CompositeActionManager) -> None:

        self._configuration = configuration
        self._resources = resources
        self._action_store = resources.action_store
        self._policy = policy
        self._messaging = messaging
        self._cam = composite_action_manager

        self._action_store.add(ActionDescription(
            id="cam:component:tcp_flow",
            type=ActionType.COMPONENT,
            platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
            description="A component message representing a single TCP flow",
            parameters=[
                ActionParameter(type=ActionParameterType.NONE, name="direction",
                                domain=configuration.action.create_action_parameter_domain_options("forward", ["forward", "reverse"])),
                ActionParameter(type=ActionParameterType.NONE, name="byte_size",
                                domain=configuration.action.create_action_parameter_domain_range(24, min=1, max=4096))
            ]
        ))

        self._action_store.add(ActionDescription(
            id="cam:direct:scan_host",
            type=ActionType.DIRECT,
            platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
            description="Scan of a single host",
            parameters=[
                ActionParameter(type=ActionParameterType.NONE, name="type",
                                domain=configuration.action.create_action_parameter_domain_options("TCP_SYN", ["TCP_SYN", "UDP"])),
            ]
        ))

        self._action_store.add(ActionDescription(
            id="cam:composite:scan_net",
            type=ActionType.COMPOSITE,
            platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
            description="Scan of a network subnet",
            parameters=[
                ActionParameter(type=ActionParameterType.NONE, name="net", domain=configuration.action.create_action_parameter_domain_any())
            ]
        ))

        self._action_store.add(ActionDescription(
            id="cam:composite:noop_action",
            type=ActionType.COMPOSITE,
            platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
            description="Test of a high-level composite action handling",
            parameters=[]
        ))

        self._action_store.add(ActionDescription(
            id="cam:composite:noop_action_2",
            type=ActionType.COMPOSITE,
            platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
            description="Test of a high-level composite action handling",
            parameters=[]
        ))

        self._action_store.add(ActionDescription(
            id="cam:composite:delay_action",
            type=ActionType.COMPOSITE,
            platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
            description="Test of a high-level composite action handling",
            parameters=[]
        ))

        self._action_store.add(ActionDescription(
            id="cam:composite:simple_action",
            type=ActionType.COMPOSITE,
            platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
            description="Test of a high-level composite action handling",
            parameters=[]
        ))


    # TODO: The difference between effect and flow is beginning to vanish
    #       There may be some utility in unifying these two
    async def action_flow(self, message: Request) -> Tuple[int, Response]:
        action_name = "_".join(message.action.fragments)
        fn: Callable[[Request], Coroutine[Any, Any, Tuple[int, Response]]] = getattr(self, "process_" + action_name, self.process_default)
        return await fn(message)

    async def process_composite_noop_action(self, message: Request) -> Tuple[int, Response]:
        response = self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.SUCCESS),
                                                   content="Noop action finished", session=message.session, auth=message.auth)
        return 1, response

    async def process_composite_noop_action_2(self, message: Request) -> Tuple[int, Response]:
        action = self._action_store.get("cam:composite:noop_action")
        request = self._messaging.create_request(message.dst_ip, message.dst_service, action, message.session,
                                                 message.auth, message)
        await self._cam.call_action(request, 0)
        response = self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.SUCCESS),
                                                   content="Noop action 2 finished", session=message.session, auth=message.auth)
        return 1, response

    async def process_composite_delay_action(self, message: Request) -> Tuple[int, Response]:
        await self._cam.delay(10)

        response = self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.SUCCESS),
                                                   content="Delay action finished", session=message.session, auth=message.auth)
        return 1, response

    async def process_composite_simple_action(self, message: Request) -> Tuple[int, Response]:
        action = self._action_store.get("cyst:test:echo_success")
        request = self._messaging.create_request(message.dst_ip, message.dst_service, action, message.session,
                                                 message.auth, message)
        await self._cam.call_action(request, 0)

        response = self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.SUCCESS),
                                                   content="Simple action finished", session=message.session, auth=message.auth)
        return 1, response

    async def process_composite_scan_net(self, message: Request) -> Tuple[int, Response]:
        net = IPNetwork(message.action.parameters["net"].value)

        # For now, we burst all the requests at once
        tasks = []

        for ip in net.iter_hosts():
            action = self._action_store.get("cam:direct:scan_host")
            request = self._messaging.create_request(ip, "", action, original_request=message)
            tasks.append(self._cam.call_action(request, 0))

        results: List[Response] = await asyncio.gather(*tasks)
        successes = []
        failures = []
        errors = []
        for r in results:
            if r.status.value == StatusValue.SUCCESS:
                successes.append(r.src_ip)
            elif r.status.value == StatusValue.FAILURE:
                failures.append(r.src_ip)
            elif r.status.value == StatusValue.ERROR:
                errors.append(r.src_ip)

        content = {
            "success": successes,
            "failure": failures,
            "error": errors
        }

        response = self._messaging.create_response(message, status=Status(StatusOrigin.NETWORK, StatusValue.SUCCESS),
                                                   content=content, session=message.session, auth=message.auth)

        # Time represents a delay on top of all the time it took to process
        return 0, response

    def action_components(self, message: Union[Request, Response]) -> List[Action]:
        # TODO: This will probably be a table one day
        components = []
        if message.action.id == "cam:direct:scan_host":
            if message.action.parameters["type"].value == "TCP_SYN":
                if message.type == MessageType.REQUEST:
                    forward_flow = self._action_store.get("cam:component:tcp_flow")
                    forward_flow.parameters["direction"].value = "forward"
                    forward_flow.parameters["byte_size"].value = 24

                    reverse_flow = self._action_store.get("cam:component:tcp_flow")
                    reverse_flow.parameters["direction"].value = "reverse"
                    reverse_flow.parameters["byte_size"].value = 10

                    components.extend([forward_flow, reverse_flow])
                if message.type == MessageType.RESPONSE:
                    if message.status.value == StatusValue.SUCCESS:
                        forward_flow = self._action_store.get("cam:component:tcp_flow")
                        forward_flow.parameters["direction"].value = "forward"
                        forward_flow.parameters["byte_size"].value = 36

                        reverse_flow = self._action_store.get("cam:component:tcp_flow")
                        reverse_flow.parameters["direction"].value = "reverse"
                        reverse_flow.parameters["byte_size"].value = 12

                        components.extend([forward_flow, reverse_flow])
                    else:
                        forward_flow = self._action_store.get("cam:component:tcp_flow")
                        forward_flow.parameters["direction"].value = "forward"
                        forward_flow.parameters["byte_size"].value = 8

                        reverse_flow = self._action_store.get("cam:component:tcp_flow")
                        reverse_flow.parameters["direction"].value = "reverse"
                        reverse_flow.parameters["byte_size"].value = 4

                        components.extend([forward_flow, reverse_flow])
            elif message.action.parameters["type"].value == "UDP":
                pass
            else:
                # I really do not know what to do with unknown message types
                pass

        return components

    async def action_effect(self, message: Request, node: Node) -> Tuple[int, Response]:
        action_name = "_".join(message.action.fragments)
        fn: Callable[[Request, Node], Tuple[int, Response]] = getattr(self, "process_" + action_name, self.process_default)
        return fn(message, node)

    def process_default(self, message: Request, node: Node) -> Tuple[int, Response]:
        print("Could not process target effect of a message. Tag in `cam` namespace unknown. " + str(message))
        return 0, self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR), session=message.session)

    def process_direct_scan_host(self, message: Request, node: Node):
        response = self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                   session=message.session, auth=message.auth)

        return 1, response

# ----------------------------------------------------------------------------------------------------------------------
# A test infrastructure configuration
# ----------------------------------------------------------------------------------------------------------------------
target = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="bash",
            owner="root",
            version="8.1.0",
            access_level=AccessLevel.LIMITED,
            local=True,
            id="bash_service"
        ),
        PassiveServiceConfig(
            type="lighttpd",
            owner="www",
            version="1.4.62",
            access_level=AccessLevel.LIMITED,
            local=False,
            id="web_server"
        )
    ],
    shell="bash",
    traffic_processors=[],
    interfaces=[],
    id="target"
)

attacker = NodeConfig(
    active_services=[
        ActiveServiceConfig(
            type="scripted_actor",
            name="attacker",
            owner="attacker",
            access_level=AccessLevel.LIMITED,
            id="attacker_service"
        )
    ],
    passive_services=[],
    interfaces=[],
    shell="",
    traffic_processors=[],
    id="attacker_node"
)

router = RouterConfig(
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

exploit1 = ExploitConfig(
    services=[
        VulnerableServiceConfig(
            name="lighttpd",
            min_version="1.4.62",
            max_version="1.4.62"
        )
    ],
    locality=ExploitLocality.REMOTE,
    category=ExploitCategory.CODE_EXECUTION,
    id="http_exploit"
)

connection1 = ConnectionConfig(
    src_id="target",
    src_port=-1,
    dst_id="router",
    dst_port=0
)

connection2 = ConnectionConfig(
    src_id="attacker_node",
    src_port=-1,
    dst_id="router",
    dst_port=1
)


# ----------------------------------------------------------------------------------------------------------------------
# Actual test cases
# ----------------------------------------------------------------------------------------------------------------------
class CompositeActionTest(unittest.TestCase):

    def setUp(self) -> None:
        self._env = Environment.create()
        # We are bypassing private guards, but it is easier and more straightforward to do it this way for testing
        # purposes.
        self._model = self._env._behavioral_models["cam"] = CAMModel(self._env.configuration, self._env.resources,
                                                                     None, self._env.messaging, self._env._cam)

        self._env.configure(target, attacker, router, exploit1, connection1, connection2)

        self._attacker_service = self._env.configuration.general.get_object_by_id("attacker_node.attacker", Service).active_service
        self._attacker_control = self._env.configuration.service.get_service_interface(self._attacker_service, ScriptedActorControl)

        self._env.control.add_pause_on_response("attacker_node.attacker")

        self._actions = {}
        for action in self._env.resources.action_store.get_prefixed("cam"):
            self._actions[action.id] = action

        self._env.control.init()

    def tearDown(self) -> None:
        self._env.control.commit()
        self._env.cleanup()  # God knows why this is not working. This is up to my successor. That poor bastard.

    def test_0000_isolated_composite_action(self):
        noop_action = self._actions["cam:composite:noop_action"]
        self._attacker_control.execute_action("192.168.0.2", "", noop_action)

        self._env.control.run()

        response = self._attacker_control.get_last_response()
        self.assertEqual(response.content, "Noop action finished", "Isolated composite action finished")

    def test_0001_nested_composite_actions(self):
        noop_action = self._actions["cam:composite:noop_action_2"]
        self._attacker_control.execute_action("192.168.0.2", "", noop_action)

        self._env.control.run()

        response = self._attacker_control.get_last_response()
        self.assertEqual(response.content, "Noop action 2 finished", "Nested composite actions finished")

    def test_0002_composite_action_with_one_direct_action(self):
        simple_action = self._actions["cam:composite:simple_action"]
        self._attacker_control.execute_action("192.168.0.2", "", simple_action)

        self._env.control.run()

        response = self._attacker_control.get_last_response()
        self.assertEqual(response.content, "Simple action finished", "Composite action with one direct action finished")

    def test_0003_composite_action_with_complex_flow(self):
        scan_action = self._actions["cam:composite:scan_net"]
        scan_action.parameters["net"].value = "192.168.0.1/28"
        self._attacker_control.execute_action("192.168.0.2", "", scan_action)

        self._env.control.run()

        response = self._attacker_control.get_last_response()
        self.assertEqual(len(response.content["success"]), 3, "Identified correct targets in complex action flow")

    def test_0004_composite_action_with_delay(self):
        delay_action = self._actions["cam:composite:delay_action"]
        self._attacker_control.execute_action("192.168.0.2", "", delay_action)

        self._env.control.run()

        self.assertGreaterEqual(self._env.resources.clock.current_time(), 10, "Delay was applied successfully")
