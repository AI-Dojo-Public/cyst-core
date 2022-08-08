from typing import Tuple, Callable

from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.interpreter import ActionInterpreter, ActionInterpreterDescription
from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.logic.action import ActionDescription, ActionToken, ActionParameterType, ActionParameterDomain, ActionParameterDomainType, ActionParameter
from cyst.api.network.node import Node


class CYSTModel(ActionInterpreter):
    def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> None:

        self._configuration = configuration
        self._action_store = resources.action_store
        self._exploit_store = resources.exploit_store
        self._policy = policy
        self._messaging = messaging

        self._action_store.add(ActionDescription("cyst:test:echo_success",
                                                 "A testing message that returns a SERVICE|SUCCESS",
                                                 [ActionParameter(ActionParameterType.NONE, "punch_strength",
                                                                  configuration.action.create_action_parameter_domain_options("weak", ["weak", "super strong"]))],
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:test:echo_failure",
                                                 "A testing message that returns a SERVICE|FAILURE",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:test:echo_error",
                                                 "A testing message that returns a SERVICE|ERROR",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:network:create_session",
                                                 "Create a session to a destination service",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:host:get_services",
                                                 "Get list of services on target node",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:host:get_remote_services",
                                                 "Get list of services on target node",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:host:get_local_services",
                                                 "Get list of services on target node",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:compound:session_after_exploit",
                                                 "Create a session after a successful application of an exploit",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:active_service:action_1",
                                                 "A placeholder action for active services instead of dedicated behavioral model.",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:active_service:action_2",
                                                 "A placeholder action for active services instead of dedicated behavioral model.",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

        self._action_store.add(ActionDescription("cyst:active_service:action_3",
                                                 "A placeholder action for active services instead of dedicated behavioral model.",
                                                 [],  # No parameters
                                                 [(ActionToken.NONE, ActionToken.NONE)]))  # No tokens

    def evaluate(self, message: Request, node: Node) -> Tuple[int, Response]:
        if not message.action:
            raise ValueError("Action not provided")

        action_name = "_".join(message.action.fragments)
        fn: Callable[[Request, Node], Tuple[int, Response]] = getattr(self, "process_" + action_name, self.process_default)
        return fn(message, node)

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:TEST
    def process_default(self, message: Request, node: Node) -> Tuple[int, Response]:
        print("Could not evaluate message. Tag in `cyst` namespace unknown. " + str(message))
        return 0, self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR), session=message.session)

    def process_test_echo_success(self, message: Request, node: Node) -> Tuple[int, Response]:
        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=message.session, auth=message.auth)

    def process_test_echo_failure(self, message: Request, node: Node) -> Tuple[int, Response]:
        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.FAILURE),
                                                  session=message.session, auth=message.auth)

    def process_test_echo_error(self, message: Request, node: Node) -> Tuple[int, Response]:
        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.ERROR),
                                                  session=message.session, auth=message.auth)

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:NETWORK
    def process_network_create_session(self, message: Request, node: Node) -> Tuple[int, Response]:
        session = self._configuration.network.create_session_from_message(message)
        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=session, auth=message.auth)

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:HOST
    def process_host_get_services(self, message: Request, node: Node) -> Tuple[int, Response]:
        services = []
        for service in node.services.values():
            if service.passive_service:
                services.append((service.name, service.passive_service.version))
        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=message.session, auth=message.auth, content=services)

    def process_host_get_remote_services(self, message: Request, node: Node) -> Tuple[int, Response]:
        services = []
        for service in node.services.values():
            if service.passive_service and not service.passive_service.local:
                services.append((service.name, service.passive_service.version))
        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=message.session, auth=message.auth, content=services)

    def process_host_get_local_services(self, message: Request, node: Node) -> Tuple[int, Response]:
        services = []
        for service in node.services.values():
            if service.passive_service and service.passive_service.local:
                services.append((service.name, service.passive_service.version))
        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=message.session, auth=message.auth, content=services)

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:COMPOUND
    def process_compound_session_after_exploit(self, message: Request, node: Node) -> Tuple[int, Response]:
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
            return 1, self._messaging.create_response(message, Status(StatusOrigin.NODE, StatusValue.ERROR), error,
                                                      session=message.session)
        else:
            return 1, self._messaging.create_response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                      session=self._configuration.network.create_session_from_message(
                                                          message),
                                                      auth=message.auth)

    # ------------------------------------------------------------------------------------------------------------------
    # CYST:ACTIVE_SERVICE
    def process_active_service_action_1(self, message: Request, node: Node) -> Tuple[int, Response]:
        # These actions cannot be called on passive services
        return 1, self._messaging.create_response(message, Status(StatusOrigin.SYSTEM, StatusValue.ERROR),
                                                  "Cannot call active service placeholder actions on passive services.",
                                                  session=message.session)

    def process_active_service_action_2(self, message: Request, node: Node) -> Tuple[int, Response]:
        # These actions cannot be called on passive services
        return 1, self._messaging.create_response(message, Status(StatusOrigin.SYSTEM, StatusValue.ERROR),
                                                  "Cannot call active service placeholder actions on passive services.",
                                                  session=message.session)

    def process_active_service_action_3(self, message: Request, node: Node) -> Tuple[int, Response]:
        # These actions cannot be called on passive services
        return 1, self._messaging.create_response(message, Status(StatusOrigin.SYSTEM, StatusValue.ERROR),
                                                  "Cannot call active service placeholder actions on passive services.",
                                                  session=message.session)


def create_cyst_model(configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                      policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> ActionInterpreter:
    model = CYSTModel(configuration, resources, policy, messaging)
    return model


action_interpreter_description = ActionInterpreterDescription(
    "cyst",
    "Behavioral model that is equivalent to CYST actionable API",
    create_cyst_model
)
