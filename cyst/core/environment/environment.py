import argparse
import asyncio
import atexit
import functools
import logging
import os
import signal
import sys
import traceback

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from heapq import heappush, heappop
from time import localtime
from typing import Tuple, List, Union, Optional, Any, Dict, Set
from threading import Condition

from cyst.api.environment.environment import Environment
from cyst.api.environment.control import EnvironmentState, EnvironmentControl
from cyst.api.environment.configuration import EnvironmentConfiguration, GeneralConfiguration, RuntimeConfiguration
from cyst.api.environment.data_model import ActionModel
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.interpreter import ActionInterpreterDescription
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.metadata_provider import MetadataProvider
from cyst.api.environment.platform import Platform, PlatformDescription
from cyst.api.environment.platform_interface import PlatformInterface
from cyst.api.environment.platform_specification import PlatformSpecification, PlatformType
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.stores import DataStoreDescription, DataStore
from cyst.api.environment.message import Message, MessageType, Request, Response
from cyst.api.logic.behavioral_model import BehavioralModelDescription, BehavioralModel
from cyst.api.network.node import Node
from cyst.api.host.service import Service
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.utils.counter import Counter
from cyst.api.utils.duration import Duration

from cyst.core.environment.configuration import GeneralConfigurationImpl
from cyst.core.environment.configuration_action import ActionConfigurationImpl
from cyst.core.environment.configuration_exploit import ExploitConfigurationImpl
from cyst.core.environment.configuration_physical import PhysicalConfigurationImpl
from cyst.core.environment.environment_configuration import EnvironmentConfigurationImpl
from cyst.core.environment.environment_control import EnvironmentControlImpl
from cyst.core.environment.environment_messaging import EnvironmentMessagingImpl
from cyst.core.environment.environment_resources import EnvironmentResourcesImpl
from cyst.core.environment.infrastructure import EnvironmentInfrastructureImpl
from cyst.core.environment.stats import StatisticsImpl

from cyst.core.environment.stores import ServiceStoreImpl
from cyst.core.environment.external_resources import ExternalResourcesImpl
from cyst.core.logic.composite_action import CompositeActionManagerImpl
# from cyst.platform.environment.message import MessageImpl  # TODO: is this the correct import?


# Environment is unlike other core implementation given an underscore-prefixed name to let python complain about
# it being private if instantiated otherwise than via the create_environment()
class _Environment(Environment, PlatformInterface):

    def __init__(self, platform: Optional[Union[str, PlatformSpecification]] = None, run_id: str = "") -> None:
        self._time = 0
        self._start_time = localtime()
        self._message_queue: List[Tuple[int, int, Message]] = []
        self._executables: List[Tuple[float, int, Message, Optional[Service], Optional[Node]]] = []
        self._executed: Set[asyncio.Task] = set()
        self._pause = False
        self._terminate = False
        self._terminate_reason = ""
        self._initialized = False
        self._finish = False
        self._finish_reason = ""
        self._state = EnvironmentState.CREATED

        self._loop = asyncio.new_event_loop()
        self._loop.set_exception_handler(self.loop_exception_handler)

        self._run_id = run_id

        self._pause_on_request: List[str] = []
        self._pause_on_response: List[str] = []

        self._action_counts: Dict[str, int] = {}
        self._highest_action_count = 0
        self._highest_action_actor = ""
        self._active_actions: Dict[int, ActionModel] = {}

        # Interface implementations
        self._environment_control = EnvironmentControlImpl(self)
        self._environment_messaging = EnvironmentMessagingImpl(self)
        self._environment_resources = EnvironmentResourcesImpl(self)

        self._behavioral_models: Dict[str, BehavioralModel] = {}
        # TODO currently, there can be only on metadata provider for one namespace
        self._metadata_providers: Dict[str, MetadataProvider] = {}
        self._platforms: Dict[PlatformSpecification, PlatformDescription] = {}
        self._data_stores: Dict[str, DataStoreDescription] = {}

        self._general_configuration = GeneralConfigurationImpl(self)
        self._action_configuration = ActionConfigurationImpl()
        self._exploit_configuration = ExploitConfigurationImpl(self)
        self._physical_configuration = PhysicalConfigurationImpl(self)
        self._runtime_configuration = RuntimeConfiguration()

        self._platform = None
        self._platform_spec = None
        self._platform_notifier = Condition()

        self._configure_runtime()
        # Runtime configuration always has some value for run_id, so the run_id passed in the initializer takes a
        # precedence, if there is any
        self._run_id = self._runtime_configuration.run_id if not self._run_id else self._run_id

        self._register_metadata_providers()
        self._register_platforms()
        self._register_data_stores()

        # set a platform if it is requested
        if platform:
            platform_not_found = False
            platform_underspecified = False

            # This is rather ugly but is a price to pay for users to not need full specification
            if isinstance(platform, str):
                spec1 = PlatformSpecification(PlatformType.SIMULATED_TIME, platform)
                spec2 = PlatformSpecification(PlatformType.REAL_TIME, platform)

                spec1_flag = spec1 in self._platforms
                spec2_flag = spec2 in self._platforms

                if not spec1_flag and not spec2_flag == True:
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
                raise RuntimeError(f"Platform {platform} exists both as a simulation and realtime environment. Please, provide a full PlatformSpecification.")

            self._platform_spec = platform
        else:
            # When no specific platform is used, CYST simulation is set
            self._platform_spec = PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST")

        # When platform specification is finalized, create components dependent on the platform specification and
        # components the platform depends on
        self._environment_resources = EnvironmentResourcesImpl(self, self._platform_spec)
        self._service_store = ServiceStoreImpl(self._environment_messaging, self._environment_resources, self._runtime_configuration)
        self._statistics = StatisticsImpl(self._run_id)

        if not self._runtime_configuration.data_backend in self._data_stores:
            raise ValueError(f"Required data store backend '{self._runtime_configuration.data_backend}' not installed. Cannot continue.")
        self._data_store = self._data_stores[self._runtime_configuration.data_backend].creation_fn(self._run_id, self._runtime_configuration.data_backend_params)

        self._infrastructure = EnvironmentInfrastructureImpl(self._runtime_configuration, self._data_store,
                                                             self._service_store, self._statistics)

        self._platform = self._create_platform(self._platform_spec)

        # If only there was a way to make it more sane, without needing to create a completely new interface
        self._environment_resources.init_resources(self._loop, self._platform.clock)

        # When platform is initialized, create a combined configuration for behavioral models
        self._environment_configuration = EnvironmentConfigurationImpl(self._general_configuration, self._platform.configuration,
                                                                       self._action_configuration, self._exploit_configuration,
                                                                       self._physical_configuration)

        self._cam = CompositeActionManagerImpl(self._loop, self._behavioral_models, self._environment_messaging,
                                               self._environment_resources, self._general_configuration,
                                               self._data_store, self._active_actions)

        # Services and actions depend on platform being initialized
        self._register_services()
        self._register_actions()
        self._register_metadata_providers()

        # Logs
        self._message_log = logging.getLogger("messaging")
        self._system_log = logging.getLogger("system")

        signal.signal(signal.SIGINT, self._signal_handler)
        atexit.register(self.cleanup)

    def cleanup(self):
        self._loop.close()

    def _signal_handler(self, *args):
        self._terminate = True
        self._terminate_reason = "Received a SIGINT signal to terminate."

    def loop_exception_handler(self, loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
        exception_text = str(context['exception']) + "\nCall stack: \n"
        if "future" in context:
            for frame in context["future"].get_stack():
                exception_text += f"{frame.f_code.co_filename}:{frame.f_lineno} :: {frame.f_code.co_qualname}\n"
        else:
            trace = traceback.StackSummary.extract(traceback.walk_tb(context["exception"].__traceback__))
            for frame in trace:
                exception_text += f"{frame.filename}:{frame.line} :: {frame.name}\n"

        error = f"Unhandled exception in event loop. Exception: {exception_text}."
        print(error)
        self._terminate = True
        self._terminate_reason = error

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
                data_backend_params_list = [x.strip() for x in data_backend_params_serialized.split(",")]
                data_backend_params = dict([(data_backend_params_list[i], data_backend_params_list[i+1]) for i in range(0, len(data_backend_params_list), 2)])

        run_id = os.environ.get('CYST_RUN_ID')
        config_id = os.environ.get('CYST_CONFIG_ID')

        max_running_time_s = os.environ.get("CYST_MAX_RUNNING_TIME")
        if max_running_time_s:
            max_running_time = float(max_running_time_s)
        else:
            max_running_time = 0.0

        run_id_log_suffix = False
        if "CYST_RUN_ID_LOG_SUFFIX" in os.environ:
            run_id_log_suffix = True

        max_action_count_s = os.environ.get("CYST_MAX_ACTION_COUNT")
        if max_action_count_s:
            max_action_count = int(max_action_count_s)
        else:
            max_action_count = 0

        config_filename = os.environ.get('CYST_CONFIG_FILENAME')

        # All the unknown, CYST-related params
        # TODO: Where to document this?
        for k, v in os.environ.items():
            if k.startswith("CYST_"):
                name = k[5:].lower()
                self._runtime_configuration.other_params[name] = v

        # Command line (only parsing)
        cmdline_parser = argparse.ArgumentParser(description="CYST runtime configuration")

        cmdline_parser.add_argument("-c", "--config_file", type=str,
                                    help="Path to a file storing the configuration. Commandline overrides the items in configuration file.")
        cmdline_parser.add_argument("-b", "--data_backend", type=str,
                                    help="The type of a backend to use. Currently supported are: MEMORY")
        cmdline_parser.add_argument("-p", "--data_backend_parameter", action="append", nargs=2, type=str,
                                    metavar=('NAME', 'VALUE'), help="Parameters to be passed to data backend.")
        cmdline_parser.add_argument("-r", "--run_id", type=str,
                                    help="A unique identifier of a simulation run. If not specified, a UUID will be generated instead.")
        cmdline_parser.add_argument("-i", "--config_id", type=str,
                                    help="A unique identifier of simulation run configuration, which can be obtained from the data store.")
        cmdline_parser.add_argument("-t", "--max_running_time", type=float,
                                    help="An upper limit on an execution time of a run. A platform time is considered, not the real time.")
        cmdline_parser.add_argument("-a", "--max_action_count", type=int,
                                    help="An upper limit on the number of executed actions by any actor. When this count is reached, the run terminates.")
        cmdline_parser.add_argument("-s", "--run_id_log_suffix", type=bool,
                                    help="Set to true if you want log file names to have the run id as a suffix.")
        cmdline_parser.add_argument("-o", "--other_param", action="append", nargs=2, type=str, metavar=('NAME', 'VALUE'),
                                    help="Other parameters that are passed to CYST components, agents, etc.")

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

        if args.max_running_time:
            max_running_time = args.max_running_time

        if args.max_action_count:
            max_action_count = args.max_action_count

        if args.run_id_log_suffix:
            run_id_log_suffix = args.run_id_log_suffix

        if args.other_param:
            for x in args.other_param:
                name = x[0].lower()
                self._runtime_configuration.other_params[name] = x[1]

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
        if max_running_time:
            self._runtime_configuration.max_running_time = max_running_time
        if max_action_count:
            self._runtime_configuration.max_action_count = max_action_count
        self._runtime_configuration.run_id_log_suffix = run_id_log_suffix

    def configure(self, *config_item: ConfigItem, parameters: dict[str, Any] | None = None) -> Environment:
        # Preprocess all configuration items for easier platform management
        self._general_configuration.preprocess(parameters, *config_item)
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
    def execute_task(self, task: Message, service: Optional[Service] = None, node: Optional[Node] = None, delay: float = 0.0) -> Tuple[bool, int]:
        heappush(self._executables, (self._platform.clock.current_time() + delay, Counter().get("msg"), task, service, node))

        return True, 0

    def process_response(self, response: Response, delay: float = 0.0) -> Tuple[bool, int]:
        self.messaging.send_message(response, delay)
        return True, 0

    # ------------------------------------------------------------------------------------------------------------------
    # Internal functions
    # TODO: Bloody names!
    def _process_finalized_task(self, task: asyncio.Task) -> None:
        try:
            delay, response = task.result()
        except Exception:  # Too broad... yeah, whatever
            call_stack = ""
            for frame in task.get_stack():
                call_stack += f"{frame.f_code.co_filename}:{frame.f_lineno} :: {frame.f_code.co_qualname}\n"
            self._system_log.log(logging.ERROR, f"There was an exception when running a task: {repr(task.exception())}.\nCall stack:\n{call_stack}")
            self._terminate = True
            self._terminate_reason = f"There was an exception when running a task: {repr(task.exception())}."
            return

        # TODO: Leaving this here, until Duration is everywhere
        if isinstance(delay, Duration):
            delay = delay.to_float()
        self.process_response(response, delay)
        self._executed.remove(task)

    def _finalize_process_message(self, message: Message, caller_id: str, task: asyncio.Task) -> None:
        #  TODO: Do we need to process the result?
        # success, delay = task.result()
        self._executed.remove(task)

        if message.type == MessageType.RESPONSE:
            if message.id in self._active_actions:
                active_action = self._active_actions[message.id]
                active_action.set_response(message)
                self._data_store.add_action(active_action)
                del self._active_actions[message.id]

            if caller_id in self._pause_on_response:
                self._pause = True

    async def _process_async(self) -> None:
        # Message sending tasks are delegated to platforms
        # Execution of behavioral models, composite actions and external resources are handled by the environment
        current_time = self._platform.clock.current_time()
        time_jump = 0

        # Set the flag to finish if we exceed the max running time.
        if self._runtime_configuration.max_running_time > 0.0 and not self._finish:
            if current_time > self._runtime_configuration.max_running_time:
                self._finish = True
                self._finish_reason = f"Exceeded the time limit of {self._runtime_configuration.max_running_time} virtual seconds "
                self._system_log.info(f"Terminating run because we ran over the time limit of {self._runtime_configuration.max_running_time} virtual seconds.")
                return

        # Set the flag to finish if we exceed the max action count from one source.
        if self._runtime_configuration.max_action_count > 0 and not self._finish:
            if self._highest_action_count > self._runtime_configuration.max_action_count:
                self._finish = True
                self._finish_reason = f"The actor '{self._highest_action_actor}' crossed the action limit of {self._runtime_configuration.max_action_count}."
                self._system_log.info(f"Terminating run because the actor '{self._highest_action_actor}' crossed the action limit of {self._runtime_configuration.max_action_count}.")
                return

        have_something_to_do = bool(self._executables) or bool(self._executed)

        # --------------------------------------------------------------------------------------------------------------
        # Process the resources if there are any
        ext = ExternalResourcesImpl.cast_from(self._environment_resources.external)
        if self._platform_spec.type == PlatformType.SIMULATED_TIME:
            ext.collect_at(current_time)
            # Suggest a time jump if there are resources waiting to be processed. Otherwise, it would just be set to 0.
            time_jump = ext.pending()[1]
        else:
            # No time jump is suggested, because time runs its own course
            ext.collect_immediately()

        # --------------------------------------------------------------------------------------------------------------
        # We let the composite action manager start all the tasks
        # This is almost no-op if no requests are in a queue for it. And if there are, they will just be processed and
        # converted to normal messages down the line.
        # Note on that |= ... process returns bool if there is some processing being done
        cam_queues_left, composite_actions_resolving, composite_actions_processing = await self._cam.process()
        have_something_to_do |= cam_queues_left

        # --------------------------------------------------------------------------------------------------------------
        # Get the required time delta
        if self._executables:
            next_time = self._executables[0][0]
            delta = next_time - current_time
            if time_jump == 0 or delta < time_jump:
                time_jump = delta

        # --------------------------------------------------------------------------------------------------------------
        # If there are still some resources that are being worked on (i.e., process after collection) than we forbid
        # the time jump
        if ext.collecting() or composite_actions_resolving:
            time_jump = 0
            have_something_to_do = True

        # --------------------------------------------------------------------------------------------------------------
        # If there is a time to jump, instruct the platform to do so
        platform_has_something_to_do = False
        if not have_something_to_do or time_jump > 0:
            platform_has_something_to_do = await self._platform.process(time_jump)
            # Return to have the process started anew
            if platform_has_something_to_do:
                return

        # Nothing pending in queues
        if not (have_something_to_do or platform_has_something_to_do or composite_actions_resolving or composite_actions_processing or ext.active()):
            # This is here to make it explicit - we do not want to finish if we are still in INIT, as this means we are
            # still executing run() methods of active services.
            if self._state != EnvironmentState.INIT:
                self._finish = True
                self._finish_reason = "No activity pending in the run."
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

                # service.active_service.process_message(message)
                t = self._loop.create_task(service.active_service.process_message(message))
                self._executed.add(t)
                t.add_done_callback(functools.partial(self._finalize_process_message, message, caller_id))
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
                model = model_description.creation_fn(self._environment_configuration, self._environment_resources, None,
                                                      self._environment_messaging, self._infrastructure, self._cam)
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
                    str(platform_description.specification)))
            else:
                self._platforms[platform_description.specification] = platform_description

    def _register_data_stores(self) -> None:

        plugin_providers = entry_points(group="cyst.data_stores")
        for s in plugin_providers:
            data_store_description = s.load()

            if data_store_description.backend in self._data_stores:
                print(f"Data store with backend {data_store_description.backend} already registered, skipping ...")
            else:
                self._data_stores[data_store_description.backend] = data_store_description

    def _create_platform(self, specification: PlatformSpecification) -> Platform:
        if specification not in self._platforms:
            raise RuntimeError(f"Attempting to create a platform that is not registered: {specification}")

        return self._platforms[specification].creation_fn(self.platform_interface, self._general_configuration,
                                                          self.resources, self._action_configuration,
                                                          self._exploit_configuration, self._physical_configuration,
                                                          self._infrastructure)


def create_environment(platform: Optional[Union[str, PlatformSpecification]] = None, run_id: str = "") -> Environment:
    e = _Environment(platform, run_id)
    return e
