from dataclasses import dataclass
from typing import Tuple, Dict, Callable, List

from netaddr import IPAddress

from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue, StatusDetail, Message
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.platform_specification import PlatformSpecification, PlatformType
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.logic.access import AuthenticationTarget, Authorization
from cyst.api.logic.action import ActionDescription, ActionParameterType, ActionParameter, ActionType, Action
from cyst.api.logic.behavioral_model import BehavioralModel, BehavioralModelDescription
from cyst.api.logic.composite_action import CompositeActionManager
from cyst.api.network.node import Node
from cyst.api.utils.duration import Duration, msecs


@dataclass
class AuthenticationTracker:
    src_ip: str
    src_service: str
    dst_ip: str
    dst_service: str
    identity: str
    step: int
    time: int
    attempts: int


class METAModel(BehavioralModel):
    def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                 infrastructure: EnvironmentInfrastructure,
                 composite_action_manager: CompositeActionManager) -> None:

        self._configuration = configuration
        self._action_store = resources.action_store
        self._exploit_store = resources.exploit_store
        self._policy = policy
        self._messaging = messaging
        self._authentications: Dict[Tuple[str, str, str, str, str], AuthenticationTracker] = {}
        self._infrastructure = infrastructure
        self._cam = composite_action_manager

        self._action_store.add(ActionDescription(id="meta:inspect:node",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="Discovery of hosts in a network. Equivalent to ping scanning.",
                                                 parameters=[]))

        self._action_store.add(ActionDescription(id="meta:authenticate",
                                                 type=ActionType.DIRECT,
                                                 platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")],
                                                 description="Authentication against a service.",
                                                 parameters=[ActionParameter(ActionParameterType.TOKEN, "auth_token", configuration.action.create_action_parameter_domain_any())]))

    async def action_flow(self, message: Request) -> Tuple[Duration, Response]:
        raise RuntimeError("META behavioral model does not support composite actions.")

    def action_components(self, message: Message) -> List[Action]:
        # META actions are component-less
        return []

    async def action_effect(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        if not message.action:
            raise ValueError("Action not provided")

        action_name = "_".join(message.action.fragments)
        fn: Callable[[Request, Node], Tuple[Duration, Response]] = getattr(self, "process_" + action_name, self.process_default)
        return fn(message, node)

    def process_default(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        print("Could not evaluate message. Tag in `meta` namespace unknown. " + str(message))
        return msecs(0), self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR), session=message.session)

    def process_inspect_node(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        error = ""
        if message.src_ip != IPAddress("127.0.0.1"):  # Local IP has a free pass
            if not message.session:
                error = "Session not provided"
            elif message.session.end[0] not in [x.ip for x in node.interfaces]:
                error = "Session does not end in required node"

        if error:
            return msecs(0), self._messaging.create_response(message, Status(StatusOrigin.NETWORK, StatusValue.FAILURE), error, session=message.session)

        return msecs(40), self._messaging.create_response(message, Status(StatusOrigin.NODE, StatusValue.SUCCESS),
                                                          node, session=message.session, auth=message.auth)

    def process_authenticate(self, message: Request, node: Node) -> Tuple[Duration, Response]:
        # To authenticate, an actor has to go through all the phases in the authentication scheme.
        # After each factor in authentication scheme is passed, the actor is given an authorization, which enables them
        # to attempt a next step. If it is the last step, the full authorization for this authentication scheme is
        # given.

        src_node = str(message.src_ip)
        src_service = message.src_service
        dst_node = str(message.dst_ip)
        dst_service = message.dst_service

        # First of all, check if the message contains authentication token
        token_found = False
        token = None
        t = message.action.parameters.get("auth_token", None)
        if t:
            if not isinstance(t, ActionParameter):
                raise RuntimeError("Wrong object type supplied as action parameter. Type: " + str(type(t)))

            if t.type == ActionParameterType.TOKEN and t.value:
                token_found = True
                token = t.value

        if not token_found:
            return msecs(20), self._messaging.create_response(message, Status(StatusOrigin.SERVICE, StatusValue.FAILURE, StatusDetail.AUTHENTICATION_NOT_PROVIDED),
                                                              "No auth token provided", session=message.session, auth=message.auth)

        #  check if node has the target service
        s = node.services.get(dst_service)
        if s is None:
            return msecs(20), self._messaging.create_response(message, Status(StatusOrigin.SERVICE, StatusValue.FAILURE,
                                                                              StatusDetail.AUTHENTICATION_NOT_PROVIDED),
                                                              "Service does not exist on this node",
                                                              session=message.session, auth=message.auth)

        #  evaluate the token
        result = self._configuration.access.evaluate_token_for_service(s, token, node, message.dst_ip)

        if result is None:
            return msecs(20), self._messaging.create_response(message, Status(StatusOrigin.SERVICE, StatusValue.FAILURE,
                                                                              StatusDetail.AUTHENTICATION_NOT_APPLICABLE),
                                                              "Token invalid for this service", session=message.session,
                                                              auth=message.auth)

        if isinstance(result, AuthenticationTarget):
            return msecs(20), self._messaging.create_response(message, Status(StatusOrigin.SERVICE, StatusValue.FAILURE,
                                                                              StatusDetail.AUTHENTICATION_NEXT),
                                                              "Continue with next factor", session=message.session,
                                                              auth=result)

        if isinstance(result, Authorization):
            return msecs(20), self._messaging.create_response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                              "Authorized", session=message.session, auth=result)


def create_meta_model(configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                      policy: EnvironmentPolicy, messaging: EnvironmentMessaging,
                      infrastructure: EnvironmentInfrastructure,
                      composite_action_manager: CompositeActionManager) -> BehavioralModel:
    model = METAModel(configuration, resources, policy, messaging, infrastructure, composite_action_manager)
    return model


behavioral_model_description = BehavioralModelDescription(
    namespace="meta",
    description="Interpreter for auxiliary actions needed to supplement",
    creation_fn=create_meta_model,
    platform=[PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"), PlatformSpecification(PlatformType.REAL_TIME, "CYST")]
)