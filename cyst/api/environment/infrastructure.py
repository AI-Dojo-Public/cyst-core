from abc import ABC, abstractmethod

from cyst.api.environment.configuration import RuntimeConfiguration
from cyst.api.environment.stats import Statistics
from cyst.api.environment.stores import ServiceStore

class EnvironmentInfrastructure(ABC):
    """
    This interface provides access to environment resources that are aimed at behavioral models and to applications
    utilizing CYST.
    """

    @property
    @abstractmethod
    def statistics(self) -> Statistics:
        """
        Statistics track basic information about the simulation runs.

        :rtype: Statistics
        """

    @property
    @abstractmethod
    def service_store(self) -> ServiceStore:
        """
        Store for services. TODO

        :return:
        """

    @property
    @abstractmethod
    def runtime_configuration(self) -> RuntimeConfiguration:
        """
        TODO
        :return:
        """
