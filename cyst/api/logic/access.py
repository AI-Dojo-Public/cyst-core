import uuid

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, List

from cyst.api.utils.configuration import ConfigItem, get_str_uuid


class AccessLevel(IntEnum):
    NONE = 0,
    LIMITED = 1,
    ELEVATED = 2


# TODO: As of now, the Authorization represents a federated authorization, but it will be split soon-ish to local
#       and federated.
@dataclass
class AuthorizationConfig(ConfigItem):
    identity: str
    nodes: List[str]
    services: List[str]
    access_level: AccessLevel
    token: str = field(default_factory=get_str_uuid)


class Authorization(ABC):

    @property
    @abstractmethod
    def identity(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def token(self) -> Optional[uuid.UUID]:
        pass
