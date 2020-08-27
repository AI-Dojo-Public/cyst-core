import uuid

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Optional


class AccessLevel(IntEnum):
    NONE = 0,
    LIMITED = 1,
    ELEVATED = 2


class Authorization(ABC):

    @property
    @abstractmethod
    def identity(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def token(self) -> Optional[uuid.UUID]:
        pass
