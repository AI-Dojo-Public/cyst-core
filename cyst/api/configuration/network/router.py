from dataclasses import dataclass, field
from typing import List, Union
from uuid import uuid4

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.network.elements import InterfaceConfig


@dataclass
class RouterConfig(ConfigItem):
    interfaces: List[Union[InterfaceConfig]]
    id: str = field(default_factory=lambda: str(uuid4()))
