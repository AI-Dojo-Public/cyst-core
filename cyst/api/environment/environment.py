from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional, Union, Dict, Any

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.control import EnvironmentControl
from cyst.api.environment.infrastructure import EnvironmentInfrastructure
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.platform import PlatformSpecification, Platform
from cyst.api.environment.platform_interface import PlatformInterface


class Environment(ABC):
    """
    The Environment provides a highest-level interface to controlling the simulation. It consists of a number of
    lower-level interfaces that provide a specific functionality.
    """
    @property
    @abstractmethod
    def configuration(self) -> EnvironmentConfiguration:
        """
        This interface is a collection of configuration interfaces for the environment, that are split according to
        their general functionality.

        :rtype: EnvironmentConfiguration
        """

    @property
    @abstractmethod
    def control(self) -> EnvironmentControl:
        """
        This interface provides mechanisms to control the execution of actions within the simulation environment.

        :rtype: EnvironmentControl
        """

    @property
    @abstractmethod
    def messaging(self) -> EnvironmentMessaging:
        """
        This interface enables creating and sending of messages within simulation.

        :rtype: EnvironmentMessaging
        """

    # @property
    # @abstractmethod
    # def policy(self) -> EnvironmentPolicy:
        """
        This environment enables handling of authentication and authorization.

        Warning:
            This interface will be gradually phased off in favor of a new auth framework.

        :rtype: EnvironmentPolicy
        """

    @property
    @abstractmethod
    def resources(self) -> EnvironmentResources:
        """
        This interface gives access to resources, such as actions or exploits.

        :rtype: EnvironmentResources
        """

    @property
    @abstractmethod
    def platform_interface(self) -> PlatformInterface:
        """
        This interface provides means for execution platforms to execute actions and to notify the results of actions.

        :rtype: PlatformInterface
        """

    @property
    @abstractmethod
    def infrastructure(self) -> EnvironmentInfrastructure:
        """
        This interface provides access to environment resources that are aimed at behavioral models and to applications
        utilizing CYST.

        :rtype: EnvironmentInfrastructure
        """

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """
        Returns the underlying execution platform, which is CYST running on.

        :rtype: Platform
        """

    @abstractmethod
    def configure(self, *config_item: ConfigItem, parameters: Dict[str, Any] | None = None) -> 'Environment':
        """
        Configures the environment, according to provided configuration items. This function can be called repeatedly,
        however, each subsequent call replaces the previous configuration. Therefore, a configuration must be done
        at once and every later change in the environment setup must be done through the
        :class:`cyst.api.environment.configuration.EnvironmentConfiguration` interface.

        :param config_item: One or more configuration items. The number of items can be arbitrary and it is not
            order-dependent.
        :type config_item: ConfigItem

        :param parameters: Name-value mapping for configuration that supports parametrization. If none is provided,
            despite parameterizable configuration, default values are used.
        :type parameters: Dict[str, Any] | None

        :return: The configured environment. Used this way for the shorthand form:

        .. code-block:: python

            e = Environment.create().configure(*config, parameters)

        """

    @classmethod
    def create(cls, platform: Optional[Union[str, PlatformSpecification]] = None) -> 'Environment':
        """
        Creates a new instance of the environment. A program using CYST can use multiple environments, however, each
        simulation run happens only in the context of one environment.

        :return: An environment instance.
        """
        import cyst.core.environment.environment
        return cyst.core.environment.environment.create_environment(platform)
