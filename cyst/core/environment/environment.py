import argparse
import asyncio
import atexit
import copy
import functools
import logging
import os
import signal
import sys
import time

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from heapq import heappush, heappop
from time import localtime
from typing import Tuple, List, Union, Optional, Any, Dict, Set
from threading import Condition

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.environment import Environment
from cyst.api.environment.control import EnvironmentState, EnvironmentControl
from cyst.api.environment.configuration import EnvironmentConfiguration, GeneralConfiguration, NodeConfiguration, \
    ServiceConfiguration, NetworkConfiguration, ExploitConfiguration, AccessConfiguration, ActionConfiguration, RuntimeConfiguration
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.interpreter import ActionInterpreterDescription
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.metadata_provider import MetadataProvider
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.platform import Platform, PlatformDescription
from cyst.api.environment.platform_interface import PlatformInterface
from cyst.api.environment.platform_specification import PlatformSpecification, PlatformType
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.message import Message, MessageType, Request, StatusValue, StatusOrigin, Status, StatusDetail, Timeout, Response
from cyst.api.logic.access import AuthenticationToken
from cyst.api.logic.behavioral_model import BehavioralModelDescription, BehavioralModel
from cyst.api.network.node import Node
from cyst.api.network.session import Session
from cyst.api.network.firewall import FirewallRule, FirewallPolicy
from cyst.api.host.service import Service, PassiveService, ActiveService, ServiceState
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.utils.counter import Counter

from cyst.core.environment.configuration import GeneralConfigurationImpl
from cyst.core.environment.configuration_action import ActionConfigurationImpl
from cyst.core.environment.configuration_exploit import ExploitConfigurationImpl
from cyst.core.environment.environment_configuration import EnvironmentConfigurationImpl
from cyst.core.environment.environment_control import EnvironmentControlImpl
from cyst.core.environment.environment_messaging import EnvironmentMessagingImpl
from cyst.core.environment.environment_resources import EnvironmentResourcesImpl
from cyst.core.environment.data_store import DataStore
from cyst.core.environment.infrastructure import EnvironmentInfrastructureImpl
from cyst.core.environment.stats import StatisticsImpl

from cyst.core.environment.stores import ServiceStoreImpl
from cyst.core.environment.external_resources import ExternalResourcesImpl
from cyst.core.logic.action import ActionImpl, ActionType
from cyst.core.logic.composite_action import CompositeActionManagerImpl


# Environment is unlike other core implementation given an underscore-prefixed name to let python complain about
# it being private if instantiated otherwise than via the create_environment()
class _Environment(Environment, PlatformInterface):

    def __init__(self, platform: Optional[Union[str, PlatformSpecification]]) -> None:
        self._time = 0
        self._start_time = localtime()
        self._message_queue: List[Tuple[int, int, Message]] = []
        self._executables: List[Tuple[float, int, Message, Optional[Service], Optional[Node]]] = []
        self._executed: Set[asyncio.Task] = set()
        self._pause = False
        self._terminate = False
        self._initialized = False
        self._finish = False
        self._state = EnvironmentState.INIT

        self._loop = asyncio.new_event_loop()
        self._loop.set_exception_handler(self.loop_exception_handler)

        self._run_id = ""

        self._pause_on_request: List[str] = []
        self._pause_on_response: List[str] = []

        # Interface implementations
        self._environment_control = EnvironmentControlImpl(self)
        self._environment_messaging = EnvironmentMessagingImpl(self)
        self._environment_resources = EnvironmentResourcesImpl(self)

        self._behavioral_models: Dict[str, BehavioralModel] = {}
        # TODO currently, there can be only on metadata provider for one namespace
        self._metadata_providers: Dict[str, MetadataProvider] = {}
        self._platforms: Dict[PlatformSpecification, PlatformDescription] = {}

        self._general_configuration = GeneralConfigurationImpl(self)
        self._action_configuration = ActionConfigurationImpl()
        self._exploit_configuration = ExploitConfigurationImpl(self)
        self._runtime_configuration = RuntimeConfiguration()

        self._platform = None
        self._platform_spec = None
        self._platform_notifier = Condition()

        self._configure_runtime()
        self._register_metadata_providers()
        self._register_platforms()

        # set a platform if it is requested
        if platform:
            platform_not_found = False
            platform_underspecified = False

            # This is rather ugly but is a price to pay for users to not need full specification
            if isinstance(platform, str):
                spec1 = PlatformSpecification(PlatformType.SIMULATION, platform)
                spec2 = PlatformSpecification(PlatformType.EMULATION, platform)

                spec1_flag = spec1 in self._platforms
                spec2_flag = spec2 in self._platforms

                if spec1_flag or spec2_flag == False:
                    platform_not_found = True
                elif spec1_flag and spec2_flag == True:
                    platform_underspecified = True
                else:
                    platform_not_found = False
                    platform = spec1 if spec1_flag else spec2
            else:
                platform_not_found = platform not in self._platforms

            if platform_not_found:
                raise RuntimeError(f"Platform {platform} is not registered into the system. Cannot continue.")

            if platform_underspecified:
                raise RuntimeError(f"Platform {platform} exists both as a simulation and emulation environment. Please, provide a full PlatformSpecification.")

            self._platform_spec = platform
        else:
            # When no specific platform is used, CYST simulation is set
            self._platform_spec = PlatformSpecification(PlatformType.SIMULATION, "CYST")

        # When platform specification is finalized, create components dependent on the platform specification and
        # components the platform depends on
        self._environment_resources = EnvironmentResourcesImpl(self, self._platform_spec)
        self._service_store = ServiceStoreImpl(self._environment_messaging, self._environment_resources)
        self._statistics = StatisticsImpl()
        self._infrastructure = EnvironmentInfrastructureImpl(self._runtime_configuration, self._service_store, self._statistics)

        self._platform = self._create_platform(self._platform_spec)

        # If only there was a way to make it more sane, without needing to create a completely new interface
        self._environment_resources.init_resources(self._loop, self._platform.clock)

        # When platform is initialized, create a combined configuration for behavioral models
        self._environment_configuration = EnvironmentConfigurationImpl(self._general_configuration, self._platform.configuration,
                                                                       self._action_configuration, self._exploit_configuration)

        # Initialize stores in a platform-dependent manner

        signal.signal(signal.SIGINT, self._signal_handler)

        self._cam = CompositeActionManagerImpl(self._loop, self._behavioral_models, self._environment_messaging, self._environment_resources, self._general_configuration)

        # Services and actions depend on platform being initialized
        self._register_services()
        self._register_actions()
        self._register_metadata_providers()

        self._data_store = DataStore(self._runtime_configuration.data_backend,
                                     self._runtime_configuration.data_backend_params)

        # Logs
        self._message_log = logging.getLogger("messaging")

        atexit.register(self.cleanup)

    def cleanup(self):
        self._loop.close()

    def _signal_handler(self, *args):
        self._terminate = True

    def loop_exception_handler(self, loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
        print(f"Unhandled exception in event loop. Exception: {context['exception']}. Task {context['future']}.")
        self._terminate = True

    def __getstate__(self) -> dict:
        return {
            # Simple values
            "_time": self._time,
            "_start_time": self._start_time,
            "_pause": self._pause,
            "_terminate": self._terminate,
            "_initialized": self._initialized,
            "_state": self._state,
            "_run_id": self._run_id,

            # Arrays
            "_pause_on_response": self._pause_on_response,
            "_pause_on_request": self._pause_on_request,

            # Simple objects
            "_runtime_configuration": self._runtime_configuration,

            # Complex beasts
            "_service_store": self._service_store,
            "_environment_resources": self._environment_resources,
            "_metadata_providers": self._metadata_providers,
            "_network": self._network,
            "_general_configuration": self._general_configuration

            # Ignored members
            # Policy - is reinitialized, no need to serialize
            # DataStore - stays the same across serializations
            # Log - stays the same across serializations
            # All interface implementations excluding the general configuration and environment resources
        }

    def __setstate__(self, state: dict) -> None:
        self._time = state["_time"]
        self._start_time = state["_start_time"]
        self._pause = state["_pause"]
        self._terminate = state["_terminate"]
        self._initialized = state["_initialized"]
        self._state = state["_state"]
        self._run_id = state["_run_id"]

        self._pause_on_response = state["_pause_on_response"]
        self._pause_on_request = state["_pause_on_request"]

        self._runtime_configuration = state["_runtime_configuration"]

        self._service_store = state["_service_store"]
        self._environment_resources = state["_environment_resources"]
        self._metadata_providers = state["_metadata_providers"]
        self._network = state["_network"]
        self._general_configuration = state["_general_configuration"]

        self._environment_control = EnvironmentControlImpl(self)
        self._environment_messaging = EnvironmentMessagingImpl(self)

    # Replace the environment with the state of another environment. This is used for deserialization. It is explicit to
    # avoid replacing of ephemeral stuff, such as data store connections or whatnot
    def _replace(self, env: "_Environment"):
        self._time = env._time
        self._start_time = env._start_time
        self._pause = env._pause
        self._terminate = env._terminate
        self._initialized = env._initialized
        self._state = env._state
        self._run_id = env._run_id

        self._pause_on_response = env._pause_on_response
        self._pause_on_request = env._pause_on_request

        self._runtime_configuration = env._runtime_configuration

        self._service_store = env._service_store
        self._environment_resources = env._environment_resources
        self._metadata_providers = env._metadata_providers
        self._network = env._network
        self._general_configuration = env._general_configuration

    # Runtime parameters can be passed via command-line, configuration file, or through environment variables
    # In case of multiple definitions of one parameter, the order is, from the most important to least:
    #                                                            command line, configuration file, environment variables
    def _configure_runtime(self) -> None:
        # Environment
        data_backend = os.environ.get('CYST_DATA_BACKEND')
        data_backend_params: Dict[str, str] = dict()
        if data_backend:
            data_backend_params_serialized = os.environ.get('CYST_DATA_BACKEND_PARAMS')
            # we expect parameters to be given in the form "param1_name","param1_value","param2_name","param2_value",...
            if data_backend_params_serialized:
                data_backend_params = dict(tuple(x) for x in data_backend_params_serialized.split(',').islice(2))
        run_id = os.environ.get('CYST_RUN_ID')
        config_id = os.environ.get('CYST_CONFIG_ID')
        config_filename = os.environ.get('CYST_CONFIG_FILENAME')

        # Command line (only parsing)
        cmdline_parser = argparse.ArgumentParser(description="CYST runtime configuration")

        cmdline_parser.add_argument("-c", "--config_file", type=str,
                                    help="Path to a file storing the configuration. Commandline overrides the items in configuration file.")
        cmdline_parser.add_argument("-b", "--data_backend", type=str,
                                    help="The type of a backend to use. Currently supported are: REDIS")
        cmdline_parser.add_argument("-p", "--data_backend_parameter", action="append", nargs=2, type=str,
                                    metavar=('NAME', 'VALUE'), help="Parameters to be passed to data backend.")
        cmdline_parser.add_argument("-r", "--run_id", type=str,
                                    help="A unique identifier of a simulation run. If not specified, a UUID will be generated instead.")
        cmdline_parser.add_argument("-i", "--config_id", type=str,
                                    help="A unique identifier of simulation run configuration, which can be obtained from the data store.")

        args, _ = cmdline_parser.parse_known_args()
        if args.config_file:
            config_filename = args.config_file

        # --------------------------------------------------------------------------------------------------------------
        # Config file TODO
        if config_filename:
            pass
        # --------------------------------------------------------------------------------------------------------------

        # Command line argument override
        if args.data_backend:
            data_backend = args.data_backend

        if args.data_backend_parameter:
            # Convert from list of lists into a list of tuples
            data_backend_params = dict(tuple(x) for x in args.data_backend_parameter) #MYPY: typehinting lambda not really possible this way, better to ignore?

        if args.run_id:
            run_id = args.run_id

        if args.config_id:
            config_id = args.config_id

        # --------------------------------------------------------------------------------------------------------------
        if data_backend:  # Fuck, I miss oneliners
            self._runtime_configuration.data_backend = data_backend
        if data_backend_params:
            self._runtime_configuration.data_backend_params = data_backend_params
        if config_filename:
            self._runtime_configuration.config_filename = config_filename
        if run_id:
            self._runtime_configuration.run_id = run_id
        if config_id:
            self._runtime_configuration.config_id = config_id

    def configure(self, *config_item: ConfigItem) -> Environment:
        # Preprocess all configuration items for easier platform management
        self._general_configuration.preprocess(*config_item)
        # Configure general stuff
        self._general_configuration.configure()
        # Process the rest in platform
        self._platform.configure(*self._general_configuration.get_configuration())

        return self

    # ------------------------------------------------------------------------------------------------------------------
    # Environment interfaces
    # ------------------------------------------------------------------------------------------------------------------
    @property
    def general(self) -> GeneralConfiguration:
        return self._general_configuration

    @property
    def configuration(self) -> EnvironmentConfiguration:
        return self._platform.configuration

    @property
    def control(self) -> EnvironmentControl:
        return self._environment_control

    @property
    def messaging(self) -> EnvironmentMessaging:
        return self._environment_messaging

    @property
    def platform_interface(self) -> PlatformInterface:
        return self

    @property
    def platform(self) -> Platform:
        return self._platform

    @property
    def resources(self) -> EnvironmentResources:
        return self._environment_resources

    @property
    def infrastructure(self) -> EnvironmentInfrastructure:
        return self._infrastructure

    # ------------------------------------------------------------------------------------------------------------------
    # An interface between the environment and a platform
    def execute_task(self, task: Message, service: Optional[Service] = None, node: Optional[Node] = None, delay: int = 0) -> Tuple[bool, int]:
        heappush(self._executables, (self._platform.clock.current_time() + delay, Counter().get("msg"), task, service, node))

        return True, 0

    def process_response(self, response: Response, delay: float = 0) -> Tuple[bool, int]:
        self.messaging.send_message(response, int(delay))
        return True, 0

    # ------------------------------------------------------------------------------------------------------------------
    # Internal functions
    def _process_finalized_task(self, task: asyncio.Task) -> None:
        delay, response = task.result()
        self.process_response(response, delay)
        self._executed.remove(task)

    # Resource tasks are always collected as a first thing in the timeslot to supply services with data on time.
    def add_resource_task_collection(self, virtual_time: int):
        heappush(self._message_queue, (virtual_time, -1, MessageImpl(MessageType.RESOURCE)))

    def _process(self) -> Tuple[bool, EnvironmentState]:
        ri = ExternalResourcesImpl.cast_from(self._environment_resources.external)

        # The processing runs as long as there are tasks to do, composite events to process and no one ordered pause
        # or termination.
        while (self._message_queue or self._executables or self._cam.processing()) and not self._pause and not self._terminate:
            # Get the time of nearest task. It can happen that there are no tasks in the queue, but composite
            # events are being processed. In that case, the time must not jump to another time window, until all
            # composite events are processed.
            delta = -1
            if self._message_queue:
                next_time = self._message_queue[0][0]
                delta = next_time - self._time

            if self._executables:
                next_time = self._executables[0][0]
                e_delta = next_time - self._time
                if e_delta < delta or delta == -1:
                    delta = e_delta

            if self._cam.processing():
                self._cam.process(self._time)
                # If we are processing composite events, we force time to stay at the current window
                continue

            # Moving to another time window
            self._time += delta

            resources_collected = False

            current_tasks: List[MessageImpl] = []
            while self._message_queue and self._message_queue[0][0] == self._time:
                current_tasks.append(heappop(self._message_queue)[2])

            for task in current_tasks:
                if task.type == MessageType.TIMEOUT:
                    # Yay!
                    timeout = TimeoutImpl.cast_from(task.cast_to(Timeout)) #type:ignore #MYPY: Probably an issue with mypy, requires creation of helper class
                    timeout.service.process_message(task)
                # Resource messages are never traveling through the virtual network, so there can't be an issue with
                # them not being sent
                elif task.type == MessageType.RESOURCE:
                    # Resources are collected only once per timeslot
                    if not resources_collected:
                        ri.collect_tasks(self._time)
                        resources_collected = True
                else:
                    self._send_message(task)

            # Executables are a simulation-only queue. This will always be a (mostly) noop for emulated platforms
            current_executables: List[Tuple[MessageImpl, Node]] = []
            while self._executables and self._executables[0][0] <= self._time:
                e = heappop(self._executables)
                current_executables.append((e[2], e[3]))

            for e in current_executables:
                delay, response = self._execute_simulated(e[0].cast_to(Request), e[1])

                if response.status.origin == StatusOrigin.SYSTEM and response.status.value == StatusValue.ERROR: #MYPY: same as above, response None?
                   print("Could not process the request, unknown semantics.")
                else:
                   self._environment_messaging.send_message(response, delay)

        # Pause causes the system to stop processing and to keep task queue intact
        if self._pause:
            self._state = EnvironmentState.PAUSED

        # Terminate clears the task queue and sets the clock back to zero
        elif self._terminate:
            self._state = EnvironmentState.TERMINATED
            self._time = 0
            self._message_queue.clear()

        else:
            self._state = EnvironmentState.FINISHED

        return True, self._state

    async def _process_async(self) -> None:
        # Message sending tasks are delegated to platforms
        # Execution of behavioral models, composite actions and external resources are handled by the environment
        current_time = self._platform.clock.current_time()
        time_jump = 0

        have_something_to_do = bool(self._executables)

        # --------------------------------------------------------------------------------------------------------------
        # Right now, if anything is being executed, we just let the loop run, until it finishes
        if self._executed:
            return

        # --------------------------------------------------------------------------------------------------------------
        # Process the resources if there are any
        ext = ExternalResourcesImpl.cast_from(self._environment_resources.external)
        if self._platform_spec.type == PlatformType.SIMULATION:
            ext.collect_at(current_time)
            # Suggest a time jump if there are resources waiting to be processed. Otherwise, it would just be set to 0.
            time_jump = ext.pending()[1]
        else:
            # No time jump is suggested, because time runs its own course
            ext.collect_immediately()


        # --------------------------------------------------------------------------------------------------------------
        # Otherwise, we let the composite action manager start all the tasks
        # This is almost no-op if no requests are in a queue for it. And if there are, they will just be processed and
        # converted to normal messages down the line.
        # Note on that |= ... process returns bool if there is some processing being done
        cam_queues_left, composite_processing_left = await self._cam.process()
        have_something_to_do |= cam_queues_left

        # --------------------------------------------------------------------------------------------------------------
        # Get the required time delta
        if self._executables:
            next_time = self._executables[0][0]
            delta = next_time - current_time
            if time_jump == 0 or delta < time_jump:
                time_jump = delta

        # --------------------------------------------------------------------------------------------------------------
        # If there is a time to jump, instruct the platform to do so
        platform_has_something_to_do = False
        if not have_something_to_do or time_jump > 0:
            platform_has_something_to_do = await self._platform.process(time_jump)
            # Return to have the process started anew
            if platform_has_something_to_do:
                return

        # Nothing pending in queues
        if not (have_something_to_do or platform_has_something_to_do or composite_processing_left or ext.pending()[0]):
            self._finish = True
            return

        # --------------------------------------------------------------------------------------------------------------
        # Task gathering
        tasks_to_execute = []

        # Tasks scheduled for execution
        if self._executables:
            next_time = self._executables[0][0]
            while next_time <= current_time:
                task = heappop(self._executables)
                tasks_to_execute.append((task[2], task[3], task[4]))
                if self._executables:
                    next_time = self._executables[0][0]
                else:
                    break

        for task in tasks_to_execute:
            message = task[0]
            service = task[1]
            node = task[2]

            # If the task is a part of composite processing, then pass it to cam
            if self._cam.is_composite(message.id) and message.type == MessageType.RESPONSE:
                self._cam.incoming_message(message)

            # If an active service is provided, we are calling its process_message method. Otherwise, behavioral model
            # is invoked.
            elif service and service.active_service:
                # Extract and clear platform-specific information
                caller_id = ""
                if message.type == MessageType.RESPONSE:
                    caller_id = message.platform_specific["caller_id"] if "caller_id" in message.platform_specific else ""
                    message.platform_specific.clear()

                service.active_service.process_message(message)

                if message.type == MessageType.RESPONSE and caller_id in self._pause_on_response:
                    self._pause = True
            else:
                request = message.cast_to(Request)
                namespace = request.action.namespace
                t = self._loop.create_task(self._behavioral_models[namespace].action_effect(request, node))
                self._executed.add(t)
                t.add_done_callback(self._process_finalized_task)

    def _register_services(self) -> None:

        # First, check entry points registered via the importlib mechanism
        plugin_services = entry_points(group="cyst.services")
        for s in plugin_services:
            service_description = s.load()

            if self._service_store.get_service(service_description.name):
                print("Service with name {} already registered, skipping...".format(service_description.name))
            else:
                self._service_store.add_service(service_description)

        # Explicit addition of built-in active services
        # self._service_store.add_service(firewall_service_description)

    def _register_actions(self) -> None:

        plugin_models = entry_points(group="cyst.models")
        for s in plugin_models:
            model_description = s.load()

            if not isinstance(model_description, BehavioralModelDescription):
                if isinstance(model_description, ActionInterpreterDescription):
                    print(f"The model of namespace '{model_description.namespace}' uses the old API specification. "
                          f"From version 0.6.0 only BehavioralModelDescription is supported. This model will be ignored.")
                    continue
                raise RuntimeError(f"Model of unsupported type [{type(model_description)}] intercepted. Please, fix the installation.")

            model_platform = model_description.platform
            if not isinstance(model_platform, list):
                model_platform = [model_platform]

            # Skip behavioral models not supported for this platform
            if self._platform_spec not in model_platform:
                continue

            if model_description.namespace in self._behavioral_models:
                print("Behavioral model with namespace {} already registered, skipping it ...".format(
                    model_description.namespace))
            else:
                #model = model_description.creation_fn(self, self._environment_resources, self._policy,
                #                                      self._environment_messaging, self._cam)
                model = model_description.creation_fn(self._environment_configuration, self._environment_resources, None,
                                                      self._environment_messaging, self._cam)
                self._behavioral_models[model_description.namespace] = model

    def _register_metadata_providers(self) -> None:

        plugin_providers = entry_points(group="cyst.metadata_providers")
        for s in plugin_providers:
            provider_description = s.load()

            if provider_description.namespace in self._metadata_providers:
                print("Metadata provider with namespace {} already registered, skipping ...".format(
                    provider_description.namespace))
            else:
                provider = provider_description.creation_fn()
                self._metadata_providers[provider_description.namespace] = provider

    def _register_platforms(self) -> None:

        plugin_providers = entry_points(group="cyst.platforms")
        for s in plugin_providers:
            platform_description = s.load()

            if platform_description.specification in self._platforms:
                print("Platform with specification {} already registered, skipping ...".format(
                    platform_description.namespace))
            else:
                self._platforms[platform_description.specification] = platform_description

    def _create_platform(self, specification: PlatformSpecification) -> Platform:
        if specification not in self._platforms:
            raise RuntimeError(f"Attempting to create a platform that is not registered: {specification}")

        return self._platforms[specification].creation_fn(self.platform_interface, self._general_configuration,
                                                          self.resources, self._action_configuration,
                                                          self._exploit_configuration, self._infrastructure)

def create_environment(platform: Optional[Union[str, PlatformSpecification]]) -> Environment:
    e = _Environment(platform)
    return e
