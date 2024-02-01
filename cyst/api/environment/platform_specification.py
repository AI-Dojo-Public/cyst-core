from dataclasses import dataclass
from enum import Enum, auto


class PlatformType(Enum):
    SIMULATION = auto()
    EMULATION = auto()


@dataclass(frozen=True)
class PlatformSpecification:
    type: PlatformType
    provider: str
