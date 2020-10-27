from typing import Tuple

from cyst.api.logic.action import ActionDescription, ActionToken
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.interpreter import ActionInterpreter, ActionInterpreterDescription
from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue
from cyst.api.network.node import Node


class METAInterpreter(ActionInterpreter):
    def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> None:

        self._configuration = configuration
        self._action_store = resources.action_store
        self._exploit_store = resources.exploit_store
        self._policy = policy
        self._messaging = messaging

        self._action_store.add(ActionDescription("meta:inspect:node",
                                                 "Discovery of hosts in a network. Equivalent to ping scanning.",
                                                 [],
                                                 [(ActionToken.SESSION, ActionToken.NONE)]))

    def evaluate(self, message: Request, node: Node) -> Tuple[int, Response]:
        if not message.action:
            raise ValueError("Action not provided")

        action_name = "_".join(message.action.fragments)
        fn = getattr(self, "process_" + action_name, self.process_default)
        return fn(message, node)

    def process_default(self, message: Request, node: Node) -> Tuple[int, Response]:
        print("Could not evaluate message. Tag in `meta` namespace unknown. " + str(message))
        return 0, self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR), session=message.session)

    def process_inspect_node(self, message: Request, node: Node) -> Tuple[int, Response]:
        # TODO Need to find a way to enable inspection of local machine (i.e. without session). We could use
        #      message.origin and node.id, but these are not available with this interface
        error = ""
        if not message.session:
            error = "Session not provided"
        elif message.session.end not in [x.ip for x in node.interfaces]:
            error = "Session does not end in required node"

        if error:
            return 0, self._messaging.create_response(message, Status(StatusOrigin.NETWORK, StatusValue.FAILURE), error, session=message.session)

        return 1, self._messaging.create_response(message, Status(StatusOrigin.NODE, StatusValue.SUCCESS),
                                                  node, session=message.session, authorization=message.authorization)


def create_meta_interpreter(configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                            policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> ActionInterpreter:
    interpreter = METAInterpreter(configuration, resources, policy, messaging)
    return interpreter


action_interpreter_description = ActionInterpreterDescription(
    "meta",
    "Interpreter for auxiliary actions needed to supplement",
    create_meta_interpreter
)