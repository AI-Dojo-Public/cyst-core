from typing import Tuple, Callable, Union, List

from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.platform_specification import PlatformSpecification, PlatformType
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.logic.action import ActionDescription, ActionParameterType, ActionParameter, Action, ActionType
from cyst.api.logic.behavioral_model import BehavioralModel, BehavioralModelDescription
from cyst.api.logic.composite_action import CompositeActionManager
from cyst.api.network.node import Node
from cyst.api.utils.duration import Duration, msecs


class CYSTModel(BehavioralModel):
    def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 messaging: EnvironmentMessaging, infrastructure: EnvironmentInfrastructure,
                 composite_action_manager: CompositeActionManager) -> None:

        self._configuration = configuration
        self._action_store = resources.action_store
        self._exploit_store = resources.exploit_store
        self._messaging = messaging
        self._infrastructure = infrastructure
        self._cam = composite_action_manager

        self._action_store.add(ActionDescription(id="cyst:test:echo_success",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="A testing message that returns a SERVICE|SUCCESS",
                                                 parameters=[ActionParameter(ActionParameterType.NONE, "punch_strength",
                                                                             configuration.action.create_action_parameter_domain_options("weak", ["weak", "super strong"]))]))

        self._action_store.add(ActionDescription(id="cyst:test:echo_failure",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="A testing message that returns a SERVICE|FAILURE",
                                                 parameters=[]))

        self._action_store.add(ActionDescription(id="cyst:test:echo_error",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="A testing message that returns a SERVICE|ERROR",
                                                 parameters=[]))

        self._action_store.add(ActionDescription(id="cyst:network:create_session",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="Create a session to a destination service",
                                                 parameters=[]))

        self._action_store.add(ActionDescription(id="cyst:host:get_services",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="Get list of services on target node",
                                                 parameters=[]))

        self._action_store.add(ActionDescription(id="cyst:host:get_remote_services",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="Get list of services on target node",
                                                 parameters=[]))

        self._action_store.add(ActionDescription(id="cyst:host:get_local_services",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="Get list of services on target node",
                                                 parameters=[]))

        self._action_store.add(ActionDescription(id="cyst:compound:session_after_exploit",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="Create a session after a successful application of an exploit",
                                                 parameters=[]))

        self._action_store.add(ActionDescription(id="cyst:active_service:open_session",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="Open a session to an existing active service acting as forward/reverse shell.",
                                                 parameters=[]))

        self._action_store.add(ActionDescription(id="cyst:active_service:action_1",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="A placeholder action for active services instead of dedicated behavioral model.",
                                                 parameters=[]))

    async def action_flow(self, message: Request) -> Tuple[Duration, Response]:
        raise RuntimeError("CYST namespace does not support composite actions")

    async def action_effect(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        if not message.action:
            raise ValueError("Action not provided")

        action_name = "_".join(message.action.fragments)
        fn: Callable[[Request, Node], Tuple[Duration, Response]] = getattr(self, "process_" + action_name, self.process_default)
        return fn(message, node)

    def action_components(self, message: Union[Request, Response]) -> List[Action]:
        # CYST actions are component-less
        return []

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:TEST
    def process_default(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        print("Could not evaluate message. Tag in `cyst` namespace unknown. " + str(message))
        return msecs(0), self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR), session=message.session)

    def process_test_echo_success(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        return msecs(20), self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=message.session, auth=message.auth)

    def process_test_echo_failure(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        return msecs(20), self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.FAILURE),
                                                          session=message.session, auth=message.auth)

    def process_test_echo_error(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        return msecs(20), self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.ERROR),
                                                          session=message.session, auth=message.auth)

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:NETWORK
    def process_network_create_session(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        session = self._configuration.network.create_session_from_message(message)
        return msecs(40), self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                          session=session, auth=message.auth)

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:HOST
    def process_host_get_services(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        services = []
        for service in node.services.values():
            if service.passive_service:
                services.append((service.name, service.passive_service.version))
        return msecs(40), self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                          session=message.session, auth=message.auth, content=services)

    def process_host_get_remote_services(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        services = []
        for service in node.services.values():
            if service.passive_service and not service.passive_service.local:
                services.append((service.name, service.passive_service.version))
        return msecs(40), self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                          session=message.session, auth=message.auth, content=services)

    def process_host_get_local_services(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        services = []
        for service in node.services.values():
            if service.passive_service and service.passive_service.local:
                services.append((service.name, service.passive_service.version))
        return msecs(40), self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                          session=message.session, auth=message.auth, content=services)

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:COMPOUND
    def process_compound_session_after_exploit(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        # TODO: Add check if exploit category and locality is ok
        # Check if the service is running on the target
        error = ""
        if not message.dst_service:
            error = "Service for session creation not specified"
        # and that an exploit is provided
        elif not message.action.exploit:
            error = "Exploit not specified to ensure session creation"
        # and it actually works
        elif not self._exploit_store.evaluate_exploit(message.action.exploit, message, node):
            error = f"Service {message.dst_service} not exploitable using the exploit {message.action.exploit.id}"

        if error:
            return msecs(20), self._messaging.create_response(message, Status(StatusOrigin.NODE, StatusValue.ERROR), error,
                                                              session=message.session)
        else:
            return msecs(100), self._messaging.create_response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                               session=self._configuration.network.create_session_from_message(message),
                                                               auth=message.auth)

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:ACTIVE_SERVICE
    def process_active_service_action_1(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        # These actions cannot be called on passive services
        return msecs(60), self._messaging.create_response(message, Status(StatusOrigin.SYSTEM, StatusValue.ERROR),
                                                          "Cannot call active service placeholder actions on passive services.",
                                                          session=message.session)

    def process_active_service_action_2(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        # These actions cannot be called on passive services
        return msecs(60), self._messaging.create_response(message, Status(StatusOrigin.SYSTEM, StatusValue.ERROR),
                                                          "Cannot call active service placeholder actions on passive services.",
                                                          session=message.session)

    def process_active_service_action_3(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        # These actions cannot be called on passive services
        return msecs(60), self._messaging.create_response(message, Status(StatusOrigin.SYSTEM, StatusValue.ERROR),
                                                          "Cannot call active service placeholder actions on passive services.",
                                                          session=message.session)

    def process_active_service_open_session(self, message: Request, node: Node):
        # These actions cannot be called on passive services
        return msecs(40), self._messaging.create_response(message, Status(StatusOrigin.SYSTEM, StatusValue.ERROR),
                                                          "Cannot open session with service that's not an active shell service",
                                                          session=message.session)


def create_cyst_model(configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                      messaging: EnvironmentMessaging,
                      infrastructure: EnvironmentInfrastructure,
                      composite_action_manager: CompositeActionManager) -> BehavioralModel:
    model = CYSTModel(configuration, resources, messaging, infrastructure, composite_action_manager)
    return model


behavioral_model_description = BehavioralModelDescription(
    namespace="cyst",
    description="Behavioral model that is equivalent to CYST actionable API",
    creation_fn=create_cyst_model,
    platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")]
)
