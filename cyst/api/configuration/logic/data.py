from dataclasses import dataclass, field
from uuid import uuid4
from tools.serde_customized import serialize, deserialize

from cyst.api.configuration.configuration import ConfigItem


@deserialize
@serialize
@dataclass
class DataConfig(ConfigItem):
    owner: str
    description: str
    id: str = field(default_factory=lambda: str(uuid4()))
