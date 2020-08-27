from abc import ABC, abstractmethod
from enum import Enum
from flags import Flags
from typing import NamedTuple, List, Tuple, Optional

from cyst.api.logic.exploit import Exploit


class ActionParameterType(Enum):
    NONE = 0,
    ID = 1


class ActionParameter(NamedTuple):
    action_type: ActionParameterType
    value: str


class ActionToken(Flags):
    NONE = (),
    AUTH = (),
    DATA = (),
    EXPLOIT = (),
    SESSION = ()


class ActionDescription(NamedTuple):
    id: str
    description: str
    tokens: List[Tuple[ActionToken, ActionToken]]


class Action(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def namespace(self) -> str:
        pass

    @property
    @abstractmethod
    def fragments(self) -> List[str]:
        pass

    @property
    @abstractmethod
    def exploit(self) -> Exploit:
        pass

    @abstractmethod
    def set_exploit(self, exploit: Optional[Exploit]):
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[ActionParameter]:
        pass

    @abstractmethod
    def add_parameters(self, *params: ActionParameter):
        pass
