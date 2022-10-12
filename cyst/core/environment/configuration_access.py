from __future__ import annotations

import uuid

from typing import TYPE_CHECKING, List, Optional, Union, Tuple

from netaddr import IPAddress

from cyst.api.environment.configuration import AccessConfiguration
from cyst.api.host.service import Service, PassiveService
from cyst.api.logic.access import AuthenticationToken, Authorization, AuthenticationTarget, AccessScheme, \
    AuthenticationProvider, AccessLevel, AuthenticationTokenType, AuthenticationTokenSecurity, \
    AuthenticationProviderType
from cyst.api.network.node import Node

from cyst.core.host.service import PassiveServiceImpl
from cyst.core.logic.access import AuthenticationTokenImpl, AuthenticationProviderImpl, AccessSchemeImpl, \
    AuthorizationImpl, AuthenticationTargetImpl
from cyst.core.network.node import NodeImpl

if TYPE_CHECKING:
    from cyst.core.environment.environment import _Environment


class AccessConfigurationImpl(AccessConfiguration):
    def __init__(self, env: _Environment):
        self._env = env

    def create_authentication_provider(self, provider_type: AuthenticationProviderType,
                                       token_type: AuthenticationTokenType, security: AuthenticationTokenSecurity,
                                       ip: Optional[IPAddress], timeout: int, id: str = "") -> AuthenticationProvider:
        return _create_authentication_provider(self._env, provider_type, token_type, security, ip, timeout, id)

    def create_authentication_token(self, type: AuthenticationTokenType, security: AuthenticationTokenSecurity,
                                    identity: str, is_local: bool) -> AuthenticationToken:
        return AuthenticationTokenImpl(type, security, identity, is_local)._set_content(uuid.uuid4())
        # content setting is temporary until encrypted/hashed data is implemented

    def register_authentication_token(self, provider: AuthenticationProvider, token: AuthenticationToken) -> bool:
        if isinstance(provider, AuthenticationProviderImpl):
            provider.add_token(token)
            return True

        return False

    def create_and_register_authentication_token(self, provider: AuthenticationProvider, identity: str) -> Optional[
        AuthenticationToken]:
        if isinstance(provider, AuthenticationProviderImpl):
            token = self.create_authentication_token(provider.token_type, provider.security, identity,
                                                     True if provider.type == AuthenticationProviderType.LOCAL else False)
            self.register_authentication_token(provider, token)
            return token

        return None

    def create_authorization(self, identity: str, access_level: AccessLevel, id: str, nodes: Optional[List[str]] = None,
                             services: Optional[List[str]] = None) -> Authorization:
        return _create_authorization(self._env, identity, access_level, id, nodes, services)

    def create_access_scheme(self, id: str = "") -> AccessScheme:
        return _create_access_scheme(self._env, id)

    def add_provider_to_scheme(self, provider: AuthenticationProvider, scheme: AccessScheme) -> None:
        if isinstance(scheme, AccessSchemeImpl):
            scheme.add_provider(provider)
        else:
            raise RuntimeError("Attempted to provide a malformed object with AccessScheme interface")

    def add_authorization_to_scheme(self, auth: Authorization, scheme: AccessScheme) -> None:
        if isinstance(scheme, AccessSchemeImpl):
            scheme.add_authorization(auth)
            scheme.add_identity(auth.identity)
        else:
            raise RuntimeError("Attempted to provide a malformed object with AccessScheme interface")

    def evaluate_token_for_service(self, service: Service, token: AuthenticationToken, node: Node,
                                   fallback_ip: Optional[IPAddress]) -> Optional[
        Union[Authorization, AuthenticationTarget]]:
        # check if node has the service is in interpreter
        if isinstance(service, PassiveServiceImpl):
            for scheme in service.access_schemes:
                result = _assess_token(self._env, scheme, token)
                if isinstance(result, Authorization):
                    return _user_auth_create(self._env, result, service, node)
                if isinstance(result, AuthenticationTargetImpl):
                    if result.address is None:
                        result.address = fallback_ip
                    return result

        return None

    def unregister_authentication_token(self, token_identity: str, provider: AuthenticationProvider) -> None:
        AuthenticationProviderImpl.cast_from(provider).remove_token_by_identity(token_identity)

    def disable_authentication_token(self, provider: AuthenticationProvider, token: AuthenticationToken, time: int) -> None:
        AuthenticationProviderImpl.cast_from(provider).disable_token(token, time)

    def enable_authentication_token(self, provider: AuthenticationProvider, token: AuthenticationToken) -> None:
        AuthenticationProviderImpl.cast_from(provider).enable_token(token)

    def remove_authorization_from_scheme(self, auth: Authorization, scheme: AccessScheme) -> None:
        AccessSchemeImpl.cast_from(scheme).remove_authorization(auth)

    def modify_existing_access(self, service: Service, identity: str, access_level: AccessLevel) -> bool:
        if isinstance(service, PassiveService):
            ok, _ = self._access_service(service, identity, access_level, allow_modify=True)
            return ok
        return False

    def create_service_access(self, service: Service, identity: str, access_level: AccessLevel,
                              tokens: List[AuthenticationToken] = None) -> Optional[List[AuthenticationToken]]:
        if isinstance(service, PassiveService):
            ok, tokens = self._access_service(service, identity, access_level, tokens)
            if ok:
                return tokens
        return None

    @staticmethod
    def _access_service(service: PassiveService, identity: str, access_level: AccessLevel,
                        tokens: List[AuthenticationToken] = None, allow_modify: bool = False) -> Tuple[bool, List[AuthenticationToken]]:
        for scheme in PassiveServiceImpl.cast_from(service)._access_schemes:
            actual_scheme = AccessSchemeImpl.cast_from(scheme)
            if not actual_scheme.is_local():
                # TODO: handle non-local providers
                continue

            if allow_modify and identity in actual_scheme.identities:
                actual_scheme.modify_access(identity, access_level)
                return True, []

            elif not allow_modify and identity not in actual_scheme.identities:
                if tokens and not actual_scheme.match_tokens(tokens):
                    continue
                return True, actual_scheme.create_access(identity, access_level, tokens)

        return False, []


# ------------------------------------------------------------------------------------------------------------------
# Access configuration
def _create_authentication_provider(self: _Environment, provider_type: AuthenticationProviderType,
                                   token_type: AuthenticationTokenType, security: AuthenticationTokenSecurity,
                                   ip: Optional[IPAddress], timeout: int, id: str = "") -> AuthenticationProvider:
    if not id:
        id = str(uuid.uuid4())
    a = AuthenticationProviderImpl(provider_type, token_type, security, ip, timeout, id)
    self._general_configuration.add_object(a.id, a)
    return a


def _create_authorization(self: _Environment, identity: str, access_level: AccessLevel, id: str, nodes: Optional[List[str]] = None,
                         services: Optional[List[str]] = None) -> Authorization:
    if not id:
        id = str(uuid.uuid4())

    a = AuthorizationImpl(
        identity=identity,
        access_level=access_level,
        id=id,
        nodes=nodes,
        services=services
    )

    self._general_configuration.add_object(id, a)
    return a


def _create_access_scheme(self: _Environment, id: str = "") -> AccessScheme:
    if not id:
        id = str(uuid.uuid4())
    scheme = AccessSchemeImpl(id)
    self._general_configuration.add_object(scheme.id, scheme)
    return scheme


def _assess_token(self: _Environment, scheme: AccessScheme, token: AuthenticationToken) \
        -> Optional[Union[Authorization, AuthenticationTarget]]:

    for i in range(0, len(scheme.factors)):
        if scheme.factors[i][0].token_is_registered(token):
            if i == len(scheme.factors) - 1:
                return next(filter(lambda auth: auth.identity == token.identity, scheme.authorizations), None)
            else:
                return scheme.factors[i + 1][0].target
    return None


def _user_auth_create(self: _Environment, authorization: Authorization, service: Service, node: Node):
    if isinstance(authorization, AuthorizationImpl):
        if (authorization.nodes == ['*'] or NodeImpl.cast_from(node).id in authorization.nodes) and \
                (authorization.services == ['*'] or service.name in authorization.services):

            ret_auth = AuthorizationImpl(
                identity=authorization.identity,
                nodes=[NodeImpl.cast_from(node).id],
                services=[service.name],
                access_level=authorization.access_level,
                id=str(uuid.uuid4())
            )

            if isinstance(service, PassiveServiceImpl):
                service.add_active_authorization(ret_auth)  # TODO: check if this can go to public/private auths
            return ret_auth
    return None
