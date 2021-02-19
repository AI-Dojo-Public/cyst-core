from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Union, Optional
from uuid import uuid4

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.host.service import PassiveServiceConfig
from cyst.api.configuration.network.node import NodeConfig


class AccessLevel(IntEnum):
    NONE = 0,
    LIMITED = 1,
    ELEVATED = 2


@dataclass
class AuthenticationFactorConfig(ConfigItem):
    federation_domain: Optional[str]
    bound_service: Optional[Union[str, PassiveServiceConfig]]
    bound_device: Optional[Union[str, NodeConfig]]
    # The following two are mostly placeholders until user interaction is implemented
    isolated: bool = field(default=False)
    physical_access: bool = field(default=False)


# TODO: As of now, the Authorization represents a federated authorization, but it will be split soon-ish to local
#       and federated.
@dataclass
class AuthorizationConfig(ConfigItem):
    identity: str
    nodes: List[str]
    services: List[str]
    access_level: AccessLevel
    expiration: int
    token: str = field(default_factory=lambda: str(uuid4()))
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class AuthenticationSchemeConfig(ConfigItem):

    authentication_chain: List[Union[str, AuthenticationFactorConfig]]
    authorizations: List[Union[str, AuthorizationConfig]]