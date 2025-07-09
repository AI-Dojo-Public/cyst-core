from cyst.api.environment.configuration import RuntimeConfiguration
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.stats import Statistics
from cyst.api.environment.stores import ServiceStore, DataStore


class EnvironmentInfrastructureImpl(EnvironmentInfrastructure):

    def __init__(self, runtime_configuration: RuntimeConfiguration, data_store: DataStore, service_store: ServiceStore,
                 statistics: Statistics):
        self._runtime_configuration = runtime_configuration
        self._data_store = data_store
        self._service_store = service_store
        self._statistics = statistics

    @property
    def statistics(self) -> Statistics:
        return self._statistics

    @property
    def data_store(self) -> DataStore:
        return self._data_store

    @property
    def service_store(self) -> ServiceStore:
        return self._service_store

    @property
    def runtime_configuration(self) -> RuntimeConfiguration:
        return self._runtime_configuration
