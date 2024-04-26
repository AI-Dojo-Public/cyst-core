from typing import Type, Any, List, Optional

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.configuration import GeneralConfiguration, ObjectType, ConfigurationObjectType
from cyst.api.environment.platform import Platform

from cyst.platform.environment.configurator import Configurator

# ----------------------------------------------------------------------------------------------------------------------
class GeneralConfigurationImpl(GeneralConfiguration):

    def __init__(self, platform: Platform, env_general_configuration: GeneralConfiguration) -> None:
        self._configurator = Configurator(platform)
        self._env_general_configuration = env_general_configuration

    # ------------------------------------------------------------------------------------------------------------------
    # Proxy methods back to the environment
    def get_configuration(self) -> List[ConfigItem]:
        return self._env_general_configuration.get_configuration()

    def save_configuration(self, indent: Optional[int]) -> str:
        return self._env_general_configuration.save_configuration(indent)

    def load_configuration(self, config: str) -> List[ConfigItem]:
        return self._env_general_configuration.load_configuration(config)

    def get_configuration_by_id(self, id: str, configuration_type: Type[ConfigurationObjectType]) -> ConfigurationObjectType:
        return self._env_general_configuration.get_configuration_by_id(id, configuration_type)

    # ------------------------------------------------------------------------------------------------------------------
    # Local methods
    def get_object_by_id(self, id: str, object_type: Type[ObjectType]) -> ObjectType:
        return self._configurator.get_object_by_id(id, object_type)

    def add_object(self, id: str, obj: Any) -> None:
        self._configurator.add_object(id, obj)

    # Not fancying type removal, but it is unimportant here and only polutes the code
    def configure(self, *configs) -> None:
        self._configurator.configure(*configs)

    @staticmethod
    def cast_from(o: GeneralConfiguration) -> 'GeneralConfigurationImpl':
        if isinstance(o, GeneralConfigurationImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the GeneralConfiguration interface")
