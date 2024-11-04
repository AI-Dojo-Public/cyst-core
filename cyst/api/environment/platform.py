from abc import abstractmethod, ABC
from asyncio import Task
from dataclasses import dataclass
from typing import Callable

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.clock import Clock
from cyst.api.environment.configuration import EnvironmentConfiguration, GeneralConfiguration, ActionConfiguration, ExploitConfiguration, PhysicalConfiguration
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.platform_interface import PlatformInterface
from cyst.api.environment.platform_specification import PlatformSpecification
from cyst.api.environment.resources import EnvironmentResources


class Platform(ABC):
    """
    Platform interface provides an abstraction layer for different execution environments, e.g., simulation or
    emulation. When creating a new Environment a platform is instantiated and from then it takes care of message
    delivery and infrastructure configuration. As such, it is closely related to behavioral models, whose actions are
    custom tailored for a given platform.
    """

    @abstractmethod
    def init(self) -> bool:
        """
        Initialize platform. After this call, the platform should correctly process all calls. The platform need not
        check whether the init was called, the core will execute it exactly once before calling anything else.

        If the initialization was not successful, the platform should shutdown gracefully and release all resources.
        Error should be communicated via the logging interface.

        :return: True if the initialization finished successfully. False otherwise.
        """

    @abstractmethod
    def terminate(self) -> bool:
        """
        Terminate all platform operations. Within this call, all messages should be disposed of and the configured
        infrastructure should be torn down. This function will be called only once, so there is no need for checking.

        If the termination was not successful, the platform should shutdown as much as possible and indicate problems
        via the logging interface.

        :return: True if the termination finished successfully. False otherwise.
        """

    @property
    @abstractmethod
    def configuration(self) -> EnvironmentConfiguration:
        """
        The configuration interface for the entire platform. In essence, platforms may implement up-to the extent of
        CYST simulation. But it is generally understood that the configuration options for, e.g., emulation platforms
        will be much more limited and will not enable all on-the-fly modifications.

        Thus, platforms has to implement (and really implement because of usage of abstract base classes), the
        following:

        * NodeConfiguration: every method can end with exception
        * NetworkConfiguration: every method can end with exception
        * AccessConfiguration: every method can end with exception
        * ServiceConfiguration: :func:`get_service_interface` must be implemented, the rest can end with exception
        * ActionConfiguration: the one provided by the core can be used
        * ExploitConfiguration: the one provided by the core can be used
        * GeneralConfiguration:

          * :func:`get_configuration`, :func:`save_configuration`, :func:`load_configuration`, and
            :func:`get_configuration_by_id` should be proxied back to the core. :func:`get_object_by_id` must be
            implemented.

        :return: An environment configuration interface.
        """

    @abstractmethod
    def configure(self, *config_item: ConfigItem) -> 'Platform':
        """
        Configures the platform, according to provided configuration items. This function can be called repeatedly,
        however, each subsequent should replace the previous configuration. Therefore, a configuration must be done
        at once and every later change in the environment setup must be done through the
        :class:`cyst.api.environment.configuration.EnvironmentConfiguration` interface.

        :param config_item: One or more configuration items. The number of items can be arbitrary and it is not
            order-dependent.
        :type config_item: ConfigItem

        :return: The configured platform.
        """

    @property
    @abstractmethod
    def messaging(self) -> EnvironmentMessaging:
        """
        Provides access to messaging within the platform. Considering the variable nature of different platforms, they
        are expected to supply their own implementation of different messages (
        :class:`cyst.api.environment.message.Message`, :class:`cyst.api.environment.message.Request`,
        :class:`cyst.api.environment.message.Response`, :class:`cyst.api.environment.message.Timeout`). They do not have
        to implement :class:`cyst.api.environment.message.Resource`, as this is a domain of the core.

        :return: An environment messaging interface.
        """

    @abstractmethod
    async def process(self, time_advance: float) -> bool:
        """
        The main processing loop of the platform. Within this loop, the platform should process all messages that were
        enqueued through the :class:`cyst.api.environment.messaging.EnvironmentMessaging` interface.

        :param time_advance: A hint to advance the time by the specified amount of time units. The platform is free to
            ignore the parameter in real-time based systems. In simulated systems, where the time is under the control
            of the platform the time should be advanced to prevent a deadlock.
        :type time_advance: float

        :return: True if there was a message to process, False otherwise.
        """

    @property
    @abstractmethod
    def clock(self) -> Clock:
        """
        Access to a platform time management.

        :return: Clock interface.
        """


@dataclass
class PlatformDescription:
    """
    A description of a platform that is loaded as a module to CYST.

    :param specification: A platform specification that has to be unique among all loaded modules.
    :type specification: PlatformSpecification

    :param description: A textual description of the platform and its capabilities. A user-facing string.
    :type description: str

    :param creation_fn: A platform instantiation function.
    :type creation_fn: Callable[[PlatformInterface, GeneralConfiguration, EnvironmentResources, ActionConfiguration, ExploitConfiguration, EnvironmentInfrastructure], Platform]
    """
    specification: PlatformSpecification
    description: str
    creation_fn: Callable[[PlatformInterface, GeneralConfiguration, EnvironmentResources, ActionConfiguration, ExploitConfiguration, PhysicalConfiguration, EnvironmentInfrastructure], Platform]