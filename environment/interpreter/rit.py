import sys
import uuid

from typing import List, Tuple

from environment.access import Policy, Authorization, AccessLevel
from environment.action import Action, ActionList, ActionParameterType
from environment.environment import environment_interpreters
from environment.exploit import ExploitCategory, ExploitLocality, ExploitParameterType
from environment.exploit_store import ExploitStore
from environment.message import Response, Request, Status, StatusValue, StatusOrigin
from environment.network_elements import Session
from environment.node import Node

# Implemented actions
ActionList().add_action(Action("rit:active_recon:host_discovery"))
ActionList().add_action(Action("rit:active_recon:service_discovery"))
ActionList().add_action(Action("rit:active_recon:vulnerability_discovery"))
ActionList().add_action(Action("rit:active_recon:information_discovery"))
ActionList().add_action(Action("rit:privilege_escalation:user_privilege_escalation"))
ActionList().add_action(Action("rit:privilege_escalation:root_privilege_escalation"))
ActionList().add_action(Action("rit:ensure_access:command_and_control"))
ActionList().add_action(Action("rit:disclosure:data_exfiltration"))
ActionList().add_action(Action("rit:destroy:data_destruction"))

# Actions to do
ActionList().add_action(Action("rit:privilege_escalation:network_sniffing_ca"))
ActionList().add_action(Action("rit:privilege_escalation:brute_force_ca"))
ActionList().add_action(Action("rit:privilege_escalation:account_manipulation"))
ActionList().add_action(Action("rit:targeted_exploits:trusted_organization_exploitation"))
ActionList().add_action(Action("rit:targeted_exploits:exploit_public_facing_application"))
ActionList().add_action(Action("rit:targeted_exploits:exploit_remote_services"))
ActionList().add_action(Action("rit:targeted_exploits:spearphishing"))
ActionList().add_action(Action("rit:targeted_exploits:service_specific_exploitation"))
ActionList().add_action(Action("rit:targeted_exploits:arbitrary_code_execution"))
ActionList().add_action(Action("rit:ensure_access:defense_evasion"))
ActionList().add_action(Action("rit:ensure_access:lateral_movement"))
ActionList().add_action(Action("rit:zero_day:privilege_escalation"))
ActionList().add_action(Action("rit:zero_day:targeted_exploit"))
ActionList().add_action(Action("rit:zero_day:ensure_access"))
ActionList().add_action(Action("rit:disrupt:end_point_dos"))
ActionList().add_action(Action("rit:disrupt:network_dos"))
ActionList().add_action(Action("rit:disrupt:service_stop"))
ActionList().add_action(Action("rit:disrupt:resource_hijacking"))
ActionList().add_action(Action("rit:destroy:content_wipe"))
ActionList().add_action(Action("rit:distort:data_encryption"))
ActionList().add_action(Action("rit:distort:defacement"))
ActionList().add_action(Action("rit:distort:data_manipulation"))
ActionList().add_action(Action("rit:delivery:data_delivery"))


def evaluate(names: List[str], message: Request, node: Node):
    if not names:
        return 0, None

    # Gah... changing it back and forth.
    tag = "_".join(names)

    fn = getattr(sys.modules[__name__], "process_" + tag, process_default)
    return fn(message, node)


environment_interpreters["rit"] = evaluate


def process_default(message, node) -> Tuple[int, Response]:
    print("Could not evaluate message. Tag in `rit` namespace unknown. " + str(message))
    return 0, Response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR))


def process_active_recon_host_discovery(message: Request, node: Node) -> Tuple[int, Response]:
    return 1, Response(message, Status(StatusOrigin.NODE, StatusValue.SUCCESS),
                       None, session=message.session, authorization=message.authorization)


def process_active_recon_service_discovery(message: Request, node: Node) -> Tuple[int, Response]:
    # TODO Only show services, which are opened to outside
    return 1, Response(message, Status(StatusOrigin.NODE, StatusValue.SUCCESS),
                       [x for x in node.services], session=message.session, authorization=message.authorization)


def process_active_recon_vulnerability_discovery(message: Request, node: Node) -> Tuple[int, Response]:
    # TODO Only works on services, which are opened to outside
    if message.dst_service and message.dst_service in node.services:
        service_tags = [message.dst_service + "-" + str(node.services[message.dst_service].version)]
        service_tags.extend(node.services[message.dst_service].tags)
        return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                           service_tags, session=message.session, authorization=message.authorization)
    else:
        return 1, Response(message, Status(StatusOrigin.NODE, StatusValue.ERROR),
                           "No/wrong service specified for vulnerability discovery", session=message.session,
                           authorization=message.authorization)


def process_active_recon_information_discovery(message: Request, node: Node) -> Tuple[int, Response]:
    # TODO Only works on services, which are opened to outside
    if message.dst_service and message.dst_service in node.services:
        public_data = node.services[message.dst_service].public_data
        public_authorizations = node.services[message.dst_service].public_authorizations
        if public_authorizations or public_data:
            return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                               public_data + public_authorizations, session=message.session,
                               authorization=message.authorization)
        else:
            return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                               None, session=message.session,
                               authorization=message.authorization)

    return 1, Response(message, Status(StatusOrigin.NODE, StatusValue.ERROR),
                       "No/wrong service specified for vulnerability discovery", session=message.session,
                       authorization=message.authorization)


def process_ensure_access_command_and_control(message: Request, node: Node) -> Tuple[int, Response]:
    # TODO Only works on services, which are opened to outside

    # Check if the service is running on the target
    error = ""
    if not message.dst_service:
        error = "Service for session creation not specified"
    # ... and if the attacker provided either an authorization, or an exploit
    elif not message.authorization and not message.action.exploit:
        error = "Neither authorization token nor exploit specified to ensure command and control"

    if error:
        return 1, Response(message, Status(StatusOrigin.NODE, StatusValue.ERROR), error)

    # First of all, if the attacker provided an authorization token, it is tried first as it should not trigger
    # a defensive reaction
    if message.authorization:
        # Authorization without enabled session creation does not work
        if not node.services[message.dst_service].enable_session:
            error = "Service {} at node {} does not enable session creation.".format(message.dst_service, message.dst_ip)

        # check authorization and eventually create a session object to return
        elif Policy().decide(node.id, message.dst_service, node.services[message.dst_service].session_access_level, message.authorization)[0]:
            return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                               node.view(), session=Session(message.authorization.identity, message.session, message.non_session_path),
                               authorization=message.authorization)
    if message.action.exploit:
        # Successful exploit creates a new authorization, which has a service_access_level and user = service name
        if ExploitStore().evaluate(message.action.exploit.id, message.dst_service, message.session, node)[0]:
            auth = Authorization(message.dst_service, [node.id], [message.dst_service, node.shell.id],
                                 node.services[message.dst_service].service_access_level, uuid.uuid4())
            Policy().add_authorization(auth)
            return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                               node.view(), session=Session(message.dst_service, message.session, message.non_session_path),
                               authorization=auth)
        else:
            error = "Service {} not exploitable using the exploit {}".format(message.dst_service, message.action.exploit.id)

    return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), error)


def process_privilege_escalation(message: Request, node: Node, mode: str) -> Tuple[int, Response]:
    # To successfully manage a user privilege escalation, the attacker must already have an active session on the
    # target and must try to impersonate a user with same or lower access level on a service they have auth for.

    # Check if the service is running on the target
    error = ""
    if not message.dst_service:
        error = "Service for session creation not specified"

    if error:
        return 1, Response(message, Status(StatusOrigin.NODE, StatusValue.ERROR), error, session=message.session)

    # Check if exploit is correctly provided
    error = ""
    if message.action.exploit.locality != ExploitLocality.LOCAL:
        error = "User privilege escalation can only be done by a local exploit"
    elif message.action.exploit.category != ExploitCategory.AUTH_MANIPULATION:
        error = "User privilege escalation requires auth manipulation exploit"

    user_required = "root"
    impersonate_any = False
    node_ids = []
    service_ids = []

    # The parameters were changed from list to a dict, but the iteration was kept as-is, because it makes the processing
    # easier and more direct. But it should probably be revised, if the number of parameters for exploits starts to
    # grow considerably.
    for param in message.action.exploit.parameters.values():
        if param.exploit_type == ExploitParameterType.IDENTITY:
            user_required = param.value
        elif param.exploit_type == ExploitParameterType.IMPACT_IDENTITY and param.value == "ALL":
            impersonate_any = True
        elif param.exploit_type == ExploitParameterType.IMPACT_NODE and param.value == "ALL":
            node_ids = ["*"]
        elif param.exploit_type == ExploitParameterType.IMPACT_SERVICE and param.value == "ALL":
            service_ids = ["*"]

    if not node_ids:
        node_ids = [node.id]

    if not service_ids:
        service_ids = [message.dst_service]

    if mode == "user":
        if not message.action.exploit.parameters:
            error = "User privilege escalation requires one parameter - resulting user id"
        elif not impersonate_any and user_required == "root":
            error = "Either root was specified contrary to action designation or no user was provided"

    # Check if a service is to exploit is accessible
    if not message.session or message.session.endpoint.id != node.id:
        error = "No session opened to the node {} to apply local exploit".format(node.id)
    elif not message.authorization or message.dst_service not in message.authorization.services:
        error = "No previous access to a service {} available. Need to provide proper authorization".format(message.dst_service)

    if error:
        return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.ERROR), error, session=message.session)

    # Check if the exploit is applicable
    result, error = ExploitStore().evaluate(message.action.exploit.id, message.dst_service, message.session, node)

    if not result:
        return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.FAILURE), error, session=message.session)

    # Check if the provided user id is applicable
    if mode == "user" and not impersonate_any:
        user_found = False
        auths = Policy().get_authorizations(node.id, message.dst_service, AccessLevel.LIMITED)
        for auth in auths:
            if auth.identity == user_required:
                user_found = True
                break

        if not user_found:
            return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.FAILURE),
                               "Attempting to switch to a user {} who is not available at the service".format(user_required), session=message.session)

    if impersonate_any:
        user_required = "*"

    # Root exploit adds a new root user even if the user was not pre-existing
    new_auth = Authorization(user_required, node_ids, service_ids, access_level=AccessLevel.LIMITED if mode == "user" else AccessLevel.ELEVATED, token=uuid.uuid4())
    Policy().add_authorization(new_auth)

    return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "",
                       session=message.session, authorization=new_auth)


def process_privilege_escalation_root_privilege_escalation(message: Request, node: Node) -> Tuple[int, Response]:
    return process_privilege_escalation(message, node, "root")


def process_privilege_escalation_user_privilege_escalation(message: Request, node: Node) -> Tuple[int, Response]:
    return process_privilege_escalation(message, node, "user")


def process_disclosure_data_exfiltration(message: Request, node: Node) -> Tuple[int, Response]:
    # Check if the service is running on the target
    error = ""
    if not message.dst_service:
        error = "Service for session creation not specified"
    elif node.services[message.dst_service].local and (not message.session or message.session.endpoint.id != node.id):
        error = "Trying to access local service without a session to the node"

    if error:
        return 1, Response(message, Status(StatusOrigin.NODE, StatusValue.ERROR), error, session=message.session)

    service = node.services[message.dst_service]

    # Gather public data
    # TODO Public data are extracted with the information discovery action. Should it be included here?
    result = list()
    result.extend(service.public_data)

    # Go through the private data
    # Made them accessible only if the attacker has a valid authorization for given service and the authorization
    # lists them as an owner of the data
    if (message.authorization and
        message.dst_service in message.authorization.services and
        Policy().decide(node.id, message.dst_service, access_level=AccessLevel.NONE, authorization=message.authorization)):

        for datum in service.private_data:
            if message.authorization.identity == '*' or message.authorization.identity == datum.owner:
                result.append(datum)

    return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), result, session=message.session)


def process_destroy_data_destruction(message: Request, node: Node) -> Tuple[int, Response]:
    # Check if the service is running on the target
    error = ""
    if not message.dst_service:
        error = "Service for session creation not specified"
    elif node.services[message.dst_service].local and (not message.session or message.session.endpoint.id != node.id):
        error = "Trying to access local service without a session to the node"

    if error:
        return 1, Response(message, Status(StatusOrigin.NODE, StatusValue.ERROR), error, session=message.session)

    service = node.services[message.dst_service]

    # Data destruction only with authorization
    if (not message.authorization or
        message.dst_service not in message.authorization.services or
        not Policy().decide(node.id, message.dst_service, access_level=AccessLevel.NONE, authorization=message.authorization)):

        return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.FAILURE),
                           "Unauthorized attempt to delete data", session=message.session)

    # This function silently does nothing if there are no data specified for destruction
    # TODO Decide what to do, if user has an elevated access level or is a root
    if message.action.parameters:
        delete_ids = []
        new_data = []
        for param in message.action.parameters:
            if param.action_type == ActionParameterType.ID:
                # There is no checking...
                temp = uuid.UUID(param.value)
                delete_ids.append(temp)

        # Check public data
        for datum in service.public_data:
            if datum.id not in delete_ids or datum.owner != message.authorization.identity:
                new_data.append(datum)

        service.public_data.clear()
        service.public_data.extend(new_data)

        # Check private data
        new_data.clear()

        for datum in service.private_data:
            if datum.id not in delete_ids or datum.owner != message.authorization.identity:
                new_data.append(datum)

        service.private_data.clear()
        service.private_data.extend(new_data)

    return 1, Response(message, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), "", session=message.session)