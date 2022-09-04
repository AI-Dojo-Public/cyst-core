import uuid

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Optional, List, Tuple
from netaddr import IPAddress

from cyst.api.logic.data import Data


class AccessLevel(IntEnum):
    """ Access level represents in a simplified manner privileges of user, services, etc.

    Possible values:
        :NONE: No explicit access granted. This can either mean no access or guest-level access if available.
        :LIMITED: A user-level access.
        :ELEVATED: A root/superuser/administrator-level access
    """
    NONE = 0,
    LIMITED = 1,
    ELEVATED = 2


class AuthenticationTokenType(IntEnum):
    """ A type of authentication token.

    Possible values:
        :NONE: A sentinel value indicating misconfigured authentication token.
        :PASSWORD: A password-type auhentication token. Something that can be stored, shared, stolen, etc.
        :BIOMETRIC: A token that is bound to a user and cannot be appropriated unless the user is made to comply.
        :DEVICE: A physical token. Can be stolen by a human actor, but cannot be wholly manipulated by an agent.
    """
    NONE = 0,
    PASSWORD = 1,
    BIOMETRIC = 2,
    DEVICE = 3


class AuthenticationTokenSecurity(IntEnum):
    """ A security precautions on the authentication token.

    Possible values:
        :OPEN: There are no safeguards on the token. E.g, a plaintext password or any biometric.
        :SEALED: The token is hashed or encrypted for storage. E.g., /etc/shadow
        :HIDDEN: The token is never exposed. E.g., stored inside TPM.
    """
    OPEN = 0,
    SEALED = 1,
    HIDDEN = 2


class AuthenticationProviderType(IntEnum):
    """ A type of service providing an authentication.

    Possible values:
        :LOCAL: A service provides authentication for the node it resides on.
        :PROXY: A service provides authentication through another service residing on a remote node. E.g., openID.
        :REMOTE: A service provides authentication for another service on a remote node. E.g., sms or email codes.
    """
    LOCAL = 0,
    PROXY = 1,
    REMOTE = 2


class AuthenticationToken(ABC):
    """
    Authentication token represents a unit of information that can be used in one phase of authentication exchange
    to attempt to gain an authorization. It can be anything from PIN to biometrics.
    """

    @property
    @abstractmethod
    def type(self) -> AuthenticationTokenType:
        """
        Returns a type of the token

        :rtype: AuthenticationTokenType
        """
        pass

    @property
    @abstractmethod
    def security(self) -> AuthenticationTokenSecurity:
        """
        Returns a security measures of the token.

        :rtype: AuthenticationTokenSecurity
        """
        pass

    @property
    @abstractmethod
    def identity(self) -> str:
        """
        Returns or sets the identity of the token, i.e., who is associated with the token and which authorization would
        be gained if authenticated successfully.

        :getter: Returns the identity.
        :setter: Sets the identity. The token must enable setting the identity, otherwise False is returned.
        :type: str

        """
        pass

    @identity.setter
    def identity(self, value: str) -> bool:
        """
        Sets the identity of the token, i.e., who is associated with the token and which authorization would be
        gained if authenticated successfully.

        :param value: A new identity.
        :type value: str

        :return: Indication, whether the identity was correctly set.
        :rtype: bool
        """
        pass

    @abstractmethod
    def copy(self) -> Optional['AuthenticationToken']:
        """
        Creates a copy of the token.

        :rtype: AuthenticationToken
        """
        pass

    @property
    @abstractmethod
    def content(self) -> Optional[Data]:
        """
        Returns the data associated with the token. These data are mostly present with SEALED tokens, as they contained
        hashed/encrypted values that can be cracked before the token can be used.

        :rtype: Optional[Data]
        """
        pass


class AuthenticationTarget(ABC):
    """
    An authentication target represents on factor of an authentication scheme. It is a "pointer" to an existing
    service, with information about which tokens are accepted.
    """

    @property
    @abstractmethod
    def address(self) -> Optional[IPAddress]:
        """
        An IP address of the target. The address need not be present in case of local services.

        :rtype: Optional[IPAddress]
        """
        pass

    @property
    @abstractmethod
    def service(self) -> str:
        """
        A name of the service.

        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def tokens(self) -> List[AuthenticationTokenType]:
        """
        A list of token types that the service is accepting.

        :rtype: List[AuthenticationTokenType]
        """
        pass


class Authorization(ABC):
    """
    Authorization represents a set of permissions that are in effect for the given combination of identity, services
    and nodes. Aside from identity, authorization does not enable inspecting the services and nodes it is working on.
    This information must be inferred from other channels.
    """

    @property
    @abstractmethod
    def identity(self) -> Optional[str]:
        """
        The identity of the owner of this authorization.
        TODO: That Optional[] is suspicious.

        :rtype: Optional[str]
        """
        pass

    @property
    @abstractmethod
    def access_level(self) -> AccessLevel:
        """
        The access level this authorization enables.

        :rtype: AccessLevel
        """
        pass

    @property
    @abstractmethod
    def expiration(self) -> int:
        """
        A number of simulated time units this authorization will be effective from the time it was created. If the
        value is -1, then the authorization never expires.

        :rtype:int
        """
        pass

    @property
    @abstractmethod
    def token(self) -> uuid.UUID:
        """
        A unique data token. This token can be used to compare and discern two or more authorizations.

        :rtype: uuid.UUID
        """
        pass


class AuthenticationProvider(ABC):
    """
    Authentication provider is a service that enables evaluation of authentication information. Depending on its type,
    it can authenticate only against itself (as a service), or can serve as an authenticator for other services.
    """

    @property
    @abstractmethod
    def type(self) -> AuthenticationProviderType:
        """
        The type of the provider.

        :rtype: AuthenticationProviderType
        """
        pass

    @property
    @abstractmethod
    def target(self) -> AuthenticationTarget:
        """
        An authentication target of this provider, i.e., the description of this provider in the form usable within the
        authentication framework.

        :rtype: AuthenticationTarget
        """
        pass

    @abstractmethod
    def token_is_registered(self, token: AuthenticationToken) -> bool:
        """
        Checks whether the supplied authentication token is registered in this provider.

        :param token: The token to check.
        :type token: AuthenticationToken

        :return: True if token is registered, false otherwise.
        """
        pass


class AccessScheme(ABC):
    """
    The access scheme represents the highest level of authentication/authorization framework. The scheme is a set of
    authentication factors (i.e., authentication providers) with associated authorizations. A scheme is linked to a
    service and describes the steps an outside actor must undertake to get access to its resources.
    """

    @property
    @abstractmethod
    def factors(self) -> List[Tuple[AuthenticationProvider, int]]:
        """
        Returns a list of authentication factors in form of authentication providers. For each factor it includes a
        time in simulated units that an actor has, before the authentication process is terminated.

        :rtype: List[Tuple[AuthenticationProvider, int]]:
        """
        pass

    @property
    @abstractmethod
    def identities(self) -> List[str]:
        """
        Returns a list of identities that are registered with the access scheme.

        :rtype: List[str]
        """
        pass

    @property
    @abstractmethod
    def authorizations(self) -> List[Authorization]:
        """
        Returns a list of authorization templates that are associated with the scheme. These are not actual
        authorizations. TODO: Are they? I am really not sure.

        :rtype: List[Authorization]
        """
        pass
