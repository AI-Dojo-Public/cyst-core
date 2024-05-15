import logging

from asyncio import Task
from datetime import datetime
from heapq import heappop
from typing import List, Tuple, Union, Optional, Any, Callable

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.clock import Clock
from cyst.api.environment.configuration import EnvironmentConfiguration, GeneralConfiguration, NodeConfiguration, \
    ServiceConfiguration, NetworkConfiguration, ExploitConfiguration, AccessConfiguration, ActionConfiguration
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.message import Message, MessageType, Timeout
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.platform import Platform, PlatformDescription
from cyst.api.environment.platform_interface import PlatformInterface
from cyst.api.environment.platform_specification import PlatformSpecification, PlatformType
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.host.service import ActiveService
from cyst.api.network.node import Node
from cyst.api.network.session import Session

from cyst.platform.environment.configuration_access import AccessConfigurationImpl
from cyst.platform.environment.configuration_general import GeneralConfigurationImpl
from cyst.platform.environment.configuration_network import NetworkConfigurationImpl
from cyst.platform.environment.configuration_node import NodeConfigurationImpl
from cyst.platform.environment.configuration_service import ServiceConfigurationImpl
from cyst.platform.environment.configurator import Configurator
from cyst.platform.environment.message import TimeoutImpl
from cyst.platform.environment.environment_messaging import EnvironmentMessagingImpl
from cyst.platform.network.network import Network


class CYSTPlatform(Platform, EnvironmentConfiguration, Clock):
    def __init__(self, platform_interface: PlatformInterface, general_configuration: GeneralConfiguration,
                 resources: EnvironmentResources, action_configuration: ActionConfiguration,
                 exploit_configuration: ExploitConfiguration, infrastructure: EnvironmentInfrastructure):
        self._platform_interface = platform_interface
        self._resources = resources
        self._action_configuration = action_configuration
        self._exploit_configuration = exploit_configuration
        self._infrastructure = infrastructure

        self._message_log = logging.getLogger("messaging")

        self._time = 0
        self._message_queue: List[Tuple[int, int, Message]] = []
        self._execute_queue: List[Tuple[int, int, Message]] = []

        self._general_configuration = GeneralConfigurationImpl(self, general_configuration)
        self._access_configuration = AccessConfigurationImpl(self)
        self._network_configuration = NetworkConfigurationImpl(self)
        self._node_configuration = NodeConfigurationImpl(self)
        self._service_configuration = ServiceConfigurationImpl(self)

        self._network = Network(self._general_configuration)
        self._sessions_to_add: List[Tuple[str, List[Union[str, Node]], Optional[str], Optional[str], Optional[Session], bool]] = []

        self._environment_messaging = EnvironmentMessagingImpl(self)

    def init(self) -> bool:
        for session in self._sessions_to_add:
            owner = session[0]
            waypoints = session[1]
            src_service = session[2]
            dst_service = session[3]
            parent = session[4]
            reverse = session[5]

            self._network.create_session(owner, waypoints, src_service, dst_service, parent, reverse)

        return True

    def terminate(self) -> bool:
        pass

    def configure(self, *config_item: ConfigItem) -> 'Platform':
        self._general_configuration.configure(*config_item)
        return self

    # ------------------------------------------------------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------------------------------------------------------
    @property
    def configuration(self) -> EnvironmentConfiguration:
        return self

    @property
    def general(self) -> GeneralConfiguration:
        return self._general_configuration

    @property
    def node(self) -> NodeConfiguration:
        return self._node_configuration

    @property
    def service(self) -> ServiceConfiguration:
        return self._service_configuration

    @property
    def network(self) -> NetworkConfiguration:
        return self._network_configuration

    @property
    def exploit(self) -> ExploitConfiguration:
        return self._exploit_configuration

    @property
    def action(self) -> ActionConfiguration:
        return self._action_configuration

    @property
    def access(self) -> AccessConfiguration:
        return self._access_configuration

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def messaging(self) -> EnvironmentMessaging:
        return self._environment_messaging

    @property
    def policy(self) -> EnvironmentPolicy:
        pass

    @property
    def clock(self) -> Clock:
        return self

    def collect_messages(self) -> List[Message]:
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Clock interface
    def current_time(self) -> float:
        return self._time

    def real_time(self) -> datetime:
        raise NotImplementedError()

    def timeout(self, callback: Union[ActiveService, Callable[[Timeout], None]], delay: float, parameter: Any = None) -> None:
        timeout = TimeoutImpl(callback, self._time, delay, parameter)
        self._environment_messaging.send_message(timeout, int(delay))

    # ------------------------------------------------------------------------------------------------------------------
    async def process(self, time_advance: int) -> bool:

        have_something_to_do = bool(self._message_queue) or bool(self._execute_queue)
        time_jump = 0

        # Message-passing tasks
        if self._message_queue:
            next_time = self._message_queue[0][0]

            delta = next_time - self._time
            if time_jump == 0 or delta < time_jump:
                time_jump = delta

        # Request execution tasks
        if self._execute_queue:
            next_time = self._execute_queue[0][0]

            delta = next_time - self._time
            if time_jump == 0 or delta < time_jump:
                time_jump = delta

        # If there is nothing to do, just jump time as asked
        if not have_something_to_do:
            self._time += time_advance
            return False
        else:
            # If there is something to do, but it is further than the environment requested, we just move the clock and
            # do nothing
            if time_jump > time_advance:
                self._time += time_advance
                return True
            # It is sooner than the environment requested, let's do it and proceed with the rest of the code
            else:
                self._time += time_jump

        # --------------------------------------------------------------------------------------------------------------
        # Task processing
        messages_to_process = []

        if self._message_queue:
            next_time = self._message_queue[0][0]
            while next_time <= self._time:
                messages_to_process.append(heappop(self._message_queue)[2])
                if self._message_queue:
                    next_time = self._message_queue[0][0]
                else:
                    break

        for message in messages_to_process:
            if message.type == MessageType.TIMEOUT:
                # Yay!
                timeout = TimeoutImpl.cast_from(message.cast_to(Timeout))  # type:ignore #MYPY: Probably an issue with mypy, requires creation of helper class
                timeout.callback(message)
            else:
                self._environment_messaging.message_hop(message)

        tasks_to_execute = []

        if self._execute_queue:
            next_time = self._execute_queue[0][0]
            while next_time <= self._time:
                tasks_to_execute.append(heappop(self._execute_queue)[2])
                if self._execute_queue:
                    next_time = self._execute_queue[0][0]
                else:
                    break

        for task in tasks_to_execute:
            self._environment_messaging.message_process(task)

        return True


def create_platform(platform_interface: PlatformInterface, general_configuration: GeneralConfiguration,
                    resources: EnvironmentResources, action_configuration: ActionConfiguration,
                    exploit_configuration: ExploitConfiguration, infrastructure: EnvironmentInfrastructure) -> CYSTPlatform:
    p = CYSTPlatform(platform_interface, general_configuration, resources, action_configuration, exploit_configuration,
                     infrastructure)
    return p


platform_description = PlatformDescription(
    specification=PlatformSpecification(PlatformType.SIMULATION, "CYST"),
    description="A platform implementation for the CYST simulation engine.",
    creation_fn=create_platform
)
