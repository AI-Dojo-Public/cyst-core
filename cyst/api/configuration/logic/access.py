from copy import copy
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Union, Tuple
from uuid import uuid4

from netaddr import IPAddress
from tools.serde_customized import serialize

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.logic.access import AccessLevel, AuthenticationTokenSecurity, AuthenticationTokenType, \
                                  AuthenticationProviderType
from tools.serde_customized.compat import typename


@serialize
@dataclass
class AuthorizationConfig(ConfigItem):
    """ Configuration of a local authorization.

    This configuration is used as a template to produce authorization tokens after successful authentication.

    :param identity: An identity, who this authorization relates to.
    :type identity: str

    :param access_level: An access level of this particular authorization
    :type access_level: AccessLevel

    :param id: A unique identifier of the authorization configuration.
    :type id: str
    """
    identity: str
    access_level: AccessLevel
    id: str = field(default_factory=lambda: str(uuid4()))


@serialize
@dataclass
class FederatedAuthorizationConfig(ConfigItem):
    """ Configuration of a federated authorization.

    Unlike local authorization a federated authorization can span multiple services and nodes.

    This configuration is used as a template to produce authorization tokens after successful authentication.

    :param identity: An identity, who this authorization relates to.
    :type identity: str

    :param access_level: An access level of this particular authorization
    :type access_level: AccessLevel

    :param nodes: A list of node ids this authorization applies to.
    :type nodes: List[str]

    :param services: A list of service ids this authorization applies to.
    :type services: List[str]

    :param id: A unique identifier of the authorization configuration.
    :type id: str
    """
    identity: str
    access_level: AccessLevel
    nodes: List[str]
    services: List[str]
    id: str = field(default_factory=lambda: str(uuid4()))


class AuthorizationDomainType(IntEnum):
    """ Specification of an authorization domain type.

    :LOCAL: Local domain (confined to one node and service)
    :FEDERATED: Federated domain (can span multiple nodes and services)
    """
    LOCAL = 0,
    FEDERATED = 1


@serialize
@dataclass
class AuthorizationDomainConfig(ConfigItem):
    """ Configuration of an authorization domain.

    An authorization domain represents a collection of authorizations, which can then be associated with access scheme.

    :param type: A type of the domain.
    :type type: AuthorizationDomainType

    :param authorizations: A list of authorization configurations
    :type authorizations: List[Union[AuthorizationConfig, FederatedAuthorizationConfig]]

    :param id: A unique identifier of the authorization domain configuration.
    :type id: str
    """
    type: AuthorizationDomainType
    authorizations: List[Union[AuthorizationConfig, FederatedAuthorizationConfig]]
    id: str = field(default_factory=lambda: str(uuid4()))


@serialize
@dataclass
class AuthenticationProviderConfig(ConfigItem):
    """ Configuration of an authentication provider

    Authentication provider represents an authentication mechanism that can be employed in services via the access
    scheme mechanism.

    :param provider_type: The type of authentication provider.
    :type provider_type: AuthenticationProviderType

    :param token_type: The type of tokens that are employed by this authentication provider.
    :type token_type: AuthenticationTokenType

    :param token_security: Security mechanism applied to stored tokens.
    :type token_security: AuthenticationTokenSecurity

    :param id: A unique identifier of the authentication provider configuration.
    :type id: str

    :param ip: An optional IP address, which is intended for remote or federated providers. It represents an IP address
        where this provider can be accessed.
    :type ip: Optional[IPAddress]
    """
    provider_type: AuthenticationProviderType
    token_type: AuthenticationTokenType
    token_security: AuthenticationTokenSecurity
    id: str = field(default_factory=lambda: str(uuid4()))
    ip: Optional[IPAddress] = field(default=None, metadata={
        'serde_serializer': lambda x: {"cls_type": typename(type(x)), "value": str(x)},
    })
    timeout: int = 0

    # Copy stays the same, but changes the id
    def __call__(self, id: Optional[str] = None) -> 'AuthenticationProviderConfig':
        """ A copy constructor for the authentication provider configuration.

        Authentication provider configurations can be used as templates to reduce repetitions in configuration
        declarations. The first defined instance of a configuration serves as a template and the others can be used
        by creating named copies.

        Example:

        .. code-block:: python

            local_password_auth = AuthenticationProviderConfig(
                provider_type=AuthenticationProviderType.LOCAL,
                token_type=AuthenticationTokenType.PASSWORD,
                token_security=AuthenticationTokenSecurity.SEALED,
                timeout=30
            )

            ssh_provider = local_password_auth("openssh_local_pwd_auth")
        """
        new_one = copy(self)
        if id:
            new_one.id = id
        else:
            new_one.id = str(uuid4())
        return new_one


@serialize
@dataclass
class AccessSchemeConfig(ConfigItem):
    """ Configuration of an access scheme.

    An access scheme is a combination of authentication providers, which use a supplied authorization domain. An access
    scheme provides means to describe multiple authentication scheme within one service or multi-factor authentication.

    Example:

    .. code-block:: python

        PassiveServiceConfig(
            ...
            authentication_providers=[
                AuthenticationProviderConfig(
                    provider_type=AuthenticationProviderType.LOCAL,
                    token_type=AuthenticationTokenType.PASSWORD,
                    token_security=AuthenticationTokenSecurity.SEALED,
                    timeout=30,
                    id="openssh_local_pwd_auth"
                )
            ],
            access_schemes=[AccessSchemeConfig(
                authentication_providers=["openssh_local_pwd_auth"],
                authorization_domain=AuthorizationDomainConfig(
                    type=AuthorizationDomainType.LOCAL,
                    authorizations=[
                        AuthorizationConfig("user1", AccessLevel.LIMITED, id="ssh_auth_1"),
                        AuthorizationConfig("user2", AccessLevel.LIMITED, id="ssh_auth_2"),
                        AuthorizationConfig("root", AccessLevel.ELEVATED)
                    ]
                )
            )],
            ...
        )

    :param authentication_providers: A list of authentication provider ids.
    :type authentication_providers: str

    :param authorization_domain: A domain from which authorization tokens are created after successful authentication.
    :type authorization_domain: Union[AuthorizationDomainConfig, str]

    :param id: A unique identifier of the access scheme configuration.
    :type id: str
    """
    authentication_providers: List[str]
    authorization_domain: Union[AuthorizationDomainConfig, str]
    id: str = field(default_factory=lambda: str(uuid4()))
