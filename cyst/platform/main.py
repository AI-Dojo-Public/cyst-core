import logging
import asyncio
import time

from datetime import datetime
from heapq import heappop
from typing import List, Tuple, Union, Optional, Any, Callable

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.clock import Clock
from cyst.api.environment.configuration import EnvironmentConfiguration, GeneralConfiguration, NodeConfiguration, \
    ServiceConfiguration, NetworkConfiguration, ExploitConfiguration, AccessConfiguration, ActionConfiguration, \
    PhysicalConfiguration
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

from cyst.platform.host.service import Service, ServiceImpl
from cyst.platform.environment.configuration_access import AccessConfigurationImpl
from cyst.platform.environment.configuration_general import GeneralConfigurationImpl
from cyst.platform.environment.configuration_network import NetworkConfigurationImpl
from cyst.platform.environment.configuration_node import NodeConfigurationImpl
from cyst.platform.environment.configuration_service import ServiceConfigurationImpl
from cyst.platform.environment.configurator import Configurator
from cyst.platform.environment.message import TimeoutImpl
from cyst.platform.environment.environment_messaging import EnvironmentMessagingImpl
from cyst.platform.network.network import Network
from cyst.platform.network.session import SessionImpl


class CYSTPlatform(Platform, EnvironmentConfiguration, Clock):
    def __init__(self, platform_interface: PlatformInterface, general_configuration: GeneralConfiguration,
                 resources: EnvironmentResources, action_configuration: ActionConfiguration,
                 exploit_configuration: ExploitConfiguration, infrastructure: EnvironmentInfrastructure,
                 physical_configuration: PhysicalConfiguration, platform_type: PlatformType):
        self._platform_interface = platform_interface
        self._resources = resources
        self._action_configuration = action_configuration
        self._exploit_configuration = exploit_configuration
        self._physical_configuration = physical_configuration
        self._infrastructure = infrastructure
        self._platform_type = platform_type
        self._real_time_wait_factor = 0.1

        self._message_log = logging.getLogger("messaging")

        self._time = 0.0
        self._init_time = 0.0

        self._message_queue: List[Tuple[int, int, Message]] = []
        self._execute_queue: List[Tuple[int, int, Message]] = []

        self._messages_processing = 0

        self._general_configuration = GeneralConfigurationImpl(self, general_configuration)
        self._access_configuration = AccessConfigurationImpl(self)
        self._network_configuration = NetworkConfigurationImpl(self)
        self._node_configuration = NodeConfigurationImpl(self)
        self._service_configuration = ServiceConfigurationImpl(self)

        self._network = Network(self._general_configuration)
        self._sessions_to_add: List[Tuple[str, List[Union[str, Node]], Optional[str], Optional[str], Optional[Session], bool, Optional[str]]] = []

        self._environment_messaging = EnvironmentMessagingImpl(self)

    def init(self) -> bool:
        for session in self._sessions_to_add:
            owner = session[0]
            waypoints = session[1]
            src_service = session[2]
            dst_service = session[3]
            parent = session[4]
            reverse = session[5]
            id = session[6]

            s: SessionImpl = SessionImpl.cast_from(self._network.create_session(owner, waypoints, src_service, dst_service, parent, reverse, id))

            # Add sessions to services
            src_service = ServiceImpl.cast_from(self._general_configuration.get_object_by_id(f"{s.startpoint.id}.{src_service}", Service))
            dst_service = ServiceImpl.cast_from(self._general_configuration.get_object_by_id(f"{s.endpoint.id}.{dst_service}", Service))

            src_service.sessions.append(s)
            dst_service.sessions.append(s)

        self._init_time = time.time()
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

    @property
    def physical(self) -> PhysicalConfiguration:
        return self._physical_configuration

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

    # ------------------------------------------------------------------------------------------------------------------
    # Clock interface
    def current_time(self) -> float:
        if self._platform_type == PlatformType.REAL_TIME:
            self._time = time.time()

        return self._time

    def real_time(self) -> datetime:
        if self._platform_type == PlatformType.REAL_TIME:
            self._time = time.time()
            return datetime.fromtimestamp(self._time)
        else:
            return datetime.fromtimestamp(self._init_time + self._time)

    def timeout(self, callback: Union[ActiveService, Callable[[Timeout], None]], delay: float, parameter: Any = None) -> None:
        timeout = TimeoutImpl(callback, self.current_time(), delay, parameter)
        self._environment_messaging.send_message(timeout, int(delay))

    # ------------------------------------------------------------------------------------------------------------------
    def _finish_message_processing(self, task: asyncio.Task):
        self._messages_processing -= 1

    # ------------------------------------------------------------------------------------------------------------------
    async def process(self, time_advance: int) -> bool:

        if self._platform_type == PlatformType.REAL_TIME:
            self._time = time.time()

        have_something_to_do = bool(self._message_queue) or bool(self._execute_queue) or self._messages_processing > 0
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

        # Messages hopping
        # If hops are asynchronously processed, then we must not move the time forward, but we must enable processing
        # of another messages and messages hops that may arise from them.
        if self._messages_processing > 0:
            time_jump = 0

        if self._platform_type == PlatformType.SIMULATED_TIME:
            # If there is nothing to do, just jump simulated time as asked
            if not have_something_to_do:
                self._time += time_advance
                return False
            else:
                # If there is something to do, but it is further than the environment requested, we just move the clock and
                # do nothing
                if time_advance > 0 and time_jump > time_advance:
                    self._time += time_advance
                    return True
                # It is sooner than the environment requested, let's do it and proceed with the rest of the code
                else:
                    self._time += time_jump
        else:
            # We do not jump in time more than ordered
            if time_advance > 0 and time_jump > time_advance:
                time_jump = time_advance

            # We do not jump in time more than the wait factor
            if time_jump > self._real_time_wait_factor:
               time_jump = self._real_time_wait_factor

            # We jump the minimum needed
            if time_jump > 0:
                # Not async - we really want to let it wait, because we know that nothing can happen in the meantime
                # await asyncio.sleep(time_jump)
                time.sleep(time_jump)

            # And signal that we do not have anything to do
            if not have_something_to_do:
                return False

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
                t: asyncio.Task = asyncio.get_running_loop().create_task(self._environment_messaging.message_hop(message))
                t.add_done_callback(self._finish_message_processing)
                self._messages_processing += 1

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
            t: asyncio.Task = asyncio.get_running_loop().create_task(self._environment_messaging.message_process(task))
            t.add_done_callback(self._finish_message_processing)
            self._messages_processing += 1

        # Yield processing to the event loop if there are messages being processed
        if self._messages_processing > 0:
            await asyncio.sleep(0)

        return True


def create_simulated_time_platform(platform_interface: PlatformInterface, general_configuration: GeneralConfiguration,
                                   resources: EnvironmentResources, action_configuration: ActionConfiguration,
                                   exploit_configuration: ExploitConfiguration, physical_configuration: PhysicalConfiguration,
                                   infrastructure: EnvironmentInfrastructure) -> CYSTPlatform:
    p = CYSTPlatform(platform_interface, general_configuration, resources, action_configuration, exploit_configuration,
                     infrastructure, physical_configuration, PlatformType.SIMULATED_TIME)
    return p

def create_real_time_platform(platform_interface: PlatformInterface, general_configuration: GeneralConfiguration,
                              resources: EnvironmentResources, action_configuration: ActionConfiguration,
                              exploit_configuration: ExploitConfiguration, physical_configuration: PhysicalConfiguration,
                              infrastructure: EnvironmentInfrastructure) -> CYSTPlatform:
    p = CYSTPlatform(platform_interface, general_configuration, resources, action_configuration, exploit_configuration,
                     infrastructure, physical_configuration, PlatformType.REAL_TIME)
    return p


simulated_time_platform_description = PlatformDescription(
    specification=PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST"),
    description="A platform implementation for the CYST simulation engine, which is using simulated discrete time.",
    creation_fn=create_simulated_time_platform
)

real_time_platform_description = PlatformDescription(
    specification=PlatformSpecification(PlatformType.REAL_TIME, "CYST"),
    description="A platform implementation for the CYST simulation engine, which is using real time.",
    creation_fn=create_real_time_platform
)
