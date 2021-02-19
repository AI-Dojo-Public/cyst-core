import uuid

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Optional


class TokenSecurity(IntEnum):
    OPEN = 0,
    SEALED = 1,
    HIDDEN = 2


class AuthenticationToken(ABC):

    @property
    @abstractmethod
    def security(self) -> TokenSecurity:
        pass


class Authorization(ABC):

    @property
    @abstractmethod
    def identity(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def token(self) -> Optional[uuid.UUID]:
        pass

    @property
    @abstractmethod
    def expiration(self) -> int:
        pass
