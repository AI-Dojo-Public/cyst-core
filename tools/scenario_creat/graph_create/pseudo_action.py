from enum import IntEnum
from dataclasses import dataclass
from typing import List, Set


class TokenType(IntEnum):
    SERVICE = 0,
    AUTH = 1,
    SESSION = 2,
    DATA = 3,
    EXPLOIT = 4


class TokenLocality(IntEnum):
    LOCAL = 0,
    REMOTE = 1,
    NA = 9


class TokenSpecification(IntEnum):
    SERVICE = 0,
    SESSION = 1,
    DATA = 2,
    NA = 9


@dataclass
class Token:
    type: TokenType
    locality: TokenLocality = TokenLocality.NA
    specification: TokenSpecification = TokenSpecification.NA


@dataclass
class PseudoAction:
    inputs: List[Set[Token]]
    outputs: List[Set[Token]]
    name: str


ServiceToken = Token(type=TokenType.SERVICE)
DataToken = Token(type=TokenType.DATA)
GenericAuthToken = Token(type=TokenType.AUTH)
ServiceAuthToken = Token(type=TokenType.AUTH, specification=TokenSpecification.SERVICE)
SessionAuthToken = Token(type=TokenType.AUTH, specification=TokenSpecification.SESSION)
DataAuthToken = Token(type=TokenType.AUTH, specification=TokenSpecification.DATA)
GenericExploitToken = Token(type=TokenType.EXPLOIT)
LocalExploitToken = Token(type=TokenType.EXPLOIT, locality=TokenLocality.LOCAL)
RemoteExploitToken = Token(type=TokenType.EXPLOIT, locality=TokenLocality.REMOTE)
GenericSessionToken = Token(type=TokenType.SESSION)
InboundSessionToken = Token(type=TokenType.SESSION, locality=TokenLocality.LOCAL)
OutboundSessionToken = Token(type=TokenType.SESSION, locality=TokenLocality.REMOTE)


actions = [
    PseudoAction(inputs=[],
                 outputs=[{ServiceToken}],
                 name="process_active_recon_service_discovery"),
    PseudoAction(inputs=[{ServiceToken}],
                 outputs=[{}, {DataToken}, {GenericAuthToken}, {DataToken, GenericAuthToken}],
                 name="process_active_recon_information_discovery"),
    PseudoAction(inputs=[{ServiceToken, ServiceAuthToken}, {ServiceToken, RemoteExploitToken}],
                 outputs=[{InboundSessionToken}, {InboundSessionToken, ServiceAuthToken}],
                 name="process_ensure_access_command_and_control"),
    PseudoAction(inputs=[{GenericSessionToken, ServiceToken, GenericAuthToken}],
                 outputs=[{GenericAuthToken}],
                 name="process_privilege_escalation"),
    # Terminal actions
    PseudoAction(inputs=[{GenericSessionToken, ServiceToken, DataAuthToken}],
                 outputs=[{DataToken}],
                 name="process_disclosure_data_exfiltration"),
    PseudoAction(inputs=[{GenericSessionToken, ServiceToken, DataAuthToken}],
                 outputs=[],
                 name="process_disclosure_data_destruction")
]
