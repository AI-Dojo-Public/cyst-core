from cyst.api.environment.configuration import (
    EnvironmentConfiguration,
    GeneralConfiguration,
    NodeConfiguration,
    ServiceConfiguration,
    NetworkConfiguration,
    ExploitConfiguration,
    ActionConfiguration,
    AccessConfiguration,
    PhysicalConfiguration
)

class EnvironmentConfigurationImpl(EnvironmentConfiguration):
    def __init__(self, general: GeneralConfiguration, platform: EnvironmentConfiguration, action: ActionConfiguration,
                 exploit: ExploitConfiguration, physical: PhysicalConfiguration):
        self._general = general
        self._node = platform.node
        self._service = platform.service
        self._network = platform.network
        self._exploit = exploit
        self._action = action
        self._access = platform.access
        self._physical = physical

    @property
    def general(self) -> GeneralConfiguration:
        return self._general

    @property
    def node(self) -> NodeConfiguration:
        return self._node

    @property
    def service(self) -> ServiceConfiguration:
        return self._service

    @property
    def network(self) -> NetworkConfiguration:
        return self._network

    @property
    def exploit(self) -> ExploitConfiguration:
        return self._exploit

    @property
    def action(self) -> ActionConfiguration:
        return self._action

    @property
    def access(self) -> AccessConfiguration:
        return self._access

    @property
    def physical(self) -> PhysicalConfiguration:
        return self._physical
