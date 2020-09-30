from abc import ABC, abstractmethod

from cyst.api.environment.stores import ActionStore, ExploitStore


class EnvironmentResources(ABC):

    @property
    @abstractmethod
    def action_store(self) -> ActionStore:
        pass

    @property
    @abstractmethod
    def exploit_store(self) -> ExploitStore:
        pass
