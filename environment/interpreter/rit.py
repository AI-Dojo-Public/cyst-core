import sys

from typing import List, Tuple

from environment.access import Policy
from environment.action import Action, ActionList
from environment.environment import environment_interpreters
from environment.message import Response, Request, Status, StatusValue, StatusOrigin
from environment.network_elements import Session
from environment.node import PassiveNode


ActionList().add_action(Action("rit:active_recon:host_discovery"))
ActionList().add_action(Action("rit:active_recon:service_discovery"))
ActionList().add_action(Action("rit:active_recon:vulnerability_discovery"))
ActionList().add_action(Action("rit:active_recon:information_discovery"))
ActionList().add_action(Action("rit:privilege_escalation:user_privilege_escalation"))
ActionList().add_action(Action("rit:privilege_escalation:root_privilege_escalation"))
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
ActionList().add_action(Action("rit:ensure_access:command_and_control"))
ActionList().add_action(Action("rit:ensure_access:lateral_movement"))
ActionList().add_action(Action("rit:zero_day:privilege_escalation"))
ActionList().add_action(Action("rit:zero_day:targeted_exploit"))
ActionList().add_action(Action("rit:zero_day:ensure_access"))
ActionList().add_action(Action("rit:disrupt:end_point_dos"))
ActionList().add_action(Action("rit:disrupt:network_dos"))
ActionList().add_action(Action("rit:disrupt:service_stop"))
ActionList().add_action(Action("rit:disrupt:resource_hijacking"))
ActionList().add_action(Action("rit:destroy:data_destruction"))
ActionList().add_action(Action("rit:destroy:content_wipe"))
ActionList().add_action(Action("rit:distort:data_encryption"))
ActionList().add_action(Action("rit:distort:defacement"))
ActionList().add_action(Action("rit:distort:data_manipulation"))
ActionList().add_action(Action("rit:disclosure:data_exfiltration"))
ActionList().add_action(Action("rit:delivery:data_delivery"))


def evaluate(names: List[str], message: Request, node: PassiveNode):
    if not names:
        return 0, None

    # Gah... changing it back and forth.
    tag = ":".join(names)

    fn = getattr(sys.modules[__name__], "process_" + tag.replace(":", "_"), process_default)
    return fn(message, node)


environment_interpreters["rit"] = evaluate


def process_default(message, node) -> Tuple[int, Response]:
    print("Could not evaluate message. Tag in `rit` namespace unknown. " + str(message))
    return 0, Response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR))


def process_active_recon_host_discovery(message: Request, node: PassiveNode) -> Tuple[int, Response]:
    return 1, Response(message, message.service, Status(StatusOrigin.NODE, StatusValue.SUCCESS),
                       None, session=message.session, authorization=message.authorization)


def process_active_recon_service_discovery(message: Request, node: PassiveNode) -> Tuple[int, Response]:
    return 1, Response(message, message.service, Status(StatusOrigin.NODE, StatusValue.SUCCESS),
                       [x for x in node.services], session=message.session, authorization=message.authorization)


def process_active_recon_vulnerability_discovery(message: Request, node: PassiveNode) -> Tuple[int, Response]:
    if message.service and message.service in node.services:
        return 1, Response(message, message.service, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                           list(node.services[message.service].tags), session=message.session, authorization=message.authorization)
    else:
        return 1, Response(message, message.service, Status(StatusOrigin.NODE, StatusValue.ERROR),
                           "No/wrong service specified for vulnerability discovery", session=message.session,
                           authorization=message.authorization)


def process_active_recon_information_discovery(message: Request, node: PassiveNode) -> Tuple[int, Response]:
    if message.service and message.service in node.services:
        public_data = node.services[message.service].public_data
        public_authorizations = node.services[message.service].public_authorizations
        if public_authorizations or public_data:
            return 1, Response(message, message.service, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                               public_data + public_authorizations, session=message.session,
                               authorization=message.authorization)
        else:
            return 1, Response(message, message.service, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                               None, session=message.session,
                               authorization=message.authorization)

    return 1, Response(message, message.service, Status(StatusOrigin.NODE, StatusValue.ERROR),
                       "No/wrong service specified for vulnerability discovery", session=message.session,
                       authorization=message.authorization)


def process_ensure_access_command_and_control(message: Request, node: PassiveNode) -> Tuple[int, Response]:
    # Check if the target node supports session creation
    error = ""
    if not message.service:
        error = "Service for session creation not specified"
    elif message.service not in node.services:
        error = "Nonexistent service {} at node {}".format(message.service, message.dst_ip)
    elif not node.services[message.service].enable_session:
        error = "Service {} at node {} does not enable session creation.".format(message.service, message.dst_ip)

    if error:
        return 1, Response(message, message.service, Status(StatusOrigin.NODE, StatusValue.ERROR), error)

    # If it does, check authorization and eventually create a session object to return
    if Policy().decide(node.id, message.service, node.services[message.service].session_access_level, message.authorization):
        return 1, Response(message, message.service, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                           node.view(), session=Session(message.authorization.identity, message.session, message.non_session_path), authorization=message.authorization)
    else:
        return 1, Response(message, message.service, Status(StatusOrigin.SERVICE, StatusValue.FAILURE),
                           None, session=None, authorization=message.authorization)


def process_rit_privilege_escalation_user_privilege_escalation(message, node):
    # This action should only be possible on systems where an attacker has a user account and can
    return 0, None
