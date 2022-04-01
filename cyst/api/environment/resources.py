from abc import ABC, abstractmethod

from cyst.api.environment.stores import ActionStore, ExploitStore
from cyst.api.environment.stats import Statistics
from cyst.api.environment.clock import Clock


class EnvironmentResources(ABC):
    """
    This interface provides access to resources that can be used by services within the simulation.
    """

    @property
    @abstractmethod
    def action_store(self) -> ActionStore:
        """
        Through action store, services access actions that are available to them in the simulation.

        :rtype: ActionStore
        """
        pass

    @property
    @abstractmethod
    def exploit_store(self) -> ExploitStore:
        """
        Through exploit store, services access exploits that can be tied to actions.

        :rtype: ExploitStore
        """
        pass

    @property
    @abstractmethod
    def clock(self) -> Clock:
        """
        Clock provides a mean to track simulation and hybrid time.

        :rtype: Clock
        """
        pass

    @property
    @abstractmethod
    def statistics(self) -> Statistics:
        """
        Statistics track basic information about the simulation runs.

        :rtype: Statistics
        """
        pass
