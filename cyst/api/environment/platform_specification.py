from dataclasses import dataclass
from enum import Enum, auto


class PlatformType(Enum):
    """
    Differentiates the modus operandi of the platform. As there is a blurry line between the simulation and emulation,
    we differentiate them in respect their control of time.

    Possible values:

        :SIMULATED_TIME: A platform fully controls execution time.
        :REAL_TIME: A platform is operating in real-time.
    """
    SIMULATED_TIME = auto()
    REAL_TIME = auto()


@dataclass(frozen=True)
class PlatformSpecification:
    """
    A specification of a platform. Each specification must be unique among the loaded modules.

    :param type: Type of execution of the platform.
    :type type: PlatformType

    :param provider: A unique identifier of the platform. This string is used by the users to select the platform in the
        call to Environment's :func:`create` method.
    :type provider: str
    """
    type: PlatformType
    provider: str
