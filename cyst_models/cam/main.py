import asyncio
from typing import Tuple, Callable, Union, List
from netaddr import IPNetwork

from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue, MessageType
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.logic.action import ActionDescription, ActionType, ActionParameter, ActionParameterType, Action, ExecutionEnvironment, ExecutionEnvironmentType
from cyst.api.logic.behavioral_model import BehavioralModel, BehavioralModelDescription
from cyst.api.logic.composite_action import CompositeActionManager
from cyst.api.network.node import Node


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
            environment=ExecutionEnvironment(ExecutionEnvironmentType.SIMULATION, "CYST"),
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
            environment=ExecutionEnvironment(ExecutionEnvironmentType.SIMULATION, "CYST"),
            description="Scan of a single host",
            parameters=[
                ActionParameter(type=ActionParameterType.NONE, name="type",
                                domain=configuration.action.create_action_parameter_domain_options("TCP_SYN", ["TCP_SYN", "UDP"])),
            ]
        ))

        self._action_store.add(ActionDescription(
            id="cam:composite:scan_net",
            type=ActionType.COMPOSITE,
            environment=ExecutionEnvironment(ExecutionEnvironmentType.SIMULATION, "CYST"),
            description="Scan of a network subnet",
            parameters=[
                ActionParameter(type=ActionParameterType.NONE, name="net", domain=configuration.action.create_action_parameter_domain_any())
            ]
        ))

    def action_flow(self, message: Request) -> Tuple[int, Response]:
        action_name = "_".join(message.action.fragments)
        task = getattr(self, "process_" + action_name, None)
        if not task:
            raise RuntimeError("Composite action not available")

        return task(message)

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

    def action_effect(self, message: Request, node: Node) -> Tuple[int, Response]:
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


def create_cam_model(configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                     policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                     composite_action_manager: CompositeActionManager) -> BehavioralModel:
    model = CAMModel(configuration, resources, policy, messaging, composite_action_manager)
    return model


behavioral_model_description = BehavioralModelDescription(
    namespace="cam",
    description="A behavioral model for testing the new hierarchical action implementation",
    creation_fn=create_cam_model
)
