from abc import ABC, abstractmethod
from enum import Enum
from typing import Tuple


class EnvironmentState(Enum):
    INIT = 0,
    RUNNING = 1,
    PAUSED = 2,
    FINISHED = 3,
    TERMINATED = 4


class EnvironmentControl(ABC):

    @property
    @abstractmethod
    def state(self) -> EnvironmentState:
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def init(self) -> Tuple[bool, EnvironmentState]:
        pass

    @abstractmethod
    def run(self) -> Tuple[bool, EnvironmentState]:
        pass

    @abstractmethod
    def pause(self) -> Tuple[bool, EnvironmentState]:
        pass

    @abstractmethod
    def terminate(self) -> Tuple[bool, EnvironmentState]:
        pass

    @abstractmethod
    def add_pause_on_request(self, id: str) -> None:
        pass

    @abstractmethod
    def remove_pause_on_request(self, id: str) -> None:
        pass

    @abstractmethod
    def add_pause_on_response(self, id: str) -> None:
        pass

    @abstractmethod
    def remove_pause_on_response(self, id: str) -> None:
        pass
