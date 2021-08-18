from copy import copy
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Union, Tuple
from uuid import uuid4
from netaddr import IPAddress

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.logic.data import DataConfig
from cyst.api.logic.access import AccessLevel, AuthenticationTokenSecurity, AuthenticationTokenType, AuthenticationToken, \
                                  AuthenticationProviderType, AuthenticationProvider, Authorization, AuthenticationTarget, \
                                  AccessScheme


@dataclass
class AuthorizationConfig(ConfigItem):
    identity: str
    access_level: AccessLevel
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class FederatedAuthorizationConfig(ConfigItem):
    identity: str
    access_level: AccessLevel
    nodes: List[str]
    services: List[str]
    id: str = field(default_factory=lambda: str(uuid4()))


class AuthorizationDomainType(IntEnum):
    LOCAL = 0,
    FEDERATED = 1


@dataclass
class AuthorizationDomainConfig(ConfigItem):
    type: AuthorizationDomainType
    authorizations: List[Union[AuthorizationConfig, FederatedAuthorizationConfig]]
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class AuthenticationProviderConfig(ConfigItem):
    provider_type: AuthenticationProviderType
    token_type: AuthenticationTokenType
    token_security: AuthenticationTokenSecurity
    id: str = field(default_factory=lambda: str(uuid4()))
    ip: IPAddress = field(default=None)
    timeout: int = 0

    # Copy stays the same, but changes the id
    def __call__(self, id: Optional[str] = None) -> 'AuthenticationProviderConfig':
        new_one = copy(self)
        if id:
            new_one.id = id
        else:
            new_one.id = str(uuid4())
        return new_one


@dataclass
class AccessSchemeConfig(ConfigItem):
    authentication_providers: List[str]
    authorization_domain: Union[AuthorizationDomainConfig, str]
    id: str = field(default_factory=lambda: str(uuid4()))