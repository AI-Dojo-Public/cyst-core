from cyst.api.environment.configuration import RuntimeConfiguration
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.stats import Statistics
from cyst.api.environment.stores import ServiceStore

class EnvironmentInfrastructureImpl(EnvironmentInfrastructure):

    def __init__(self, runtime_configuration: RuntimeConfiguration, service_store: ServiceStore, statistics: Statistics):
        self._runtime_configuration = runtime_configuration
        self._service_store = service_store
        self._statistics = statistics

    @property
    def statistics(self) -> Statistics:
        return self._statistics

    @property
    def service_store(self) -> ServiceStore:
        return self._service_store

    @property
    def runtime_configuration(self) -> RuntimeConfiguration:
        return self._runtime_configuration
