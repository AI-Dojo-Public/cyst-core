from dataclasses import dataclass, field
from serde import serialize
from typing import Optional, List
from uuid import uuid4

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.infrastructure.log import LogConfig


@serialize
@dataclass
class InfrastructureConfig(ConfigItem):
    """
    Infrastructure configuration serves for configuring the underlying machinery that powers CYST. As such, it is
    used for log setting, simulation modes, etc.

    :param log: Configuration of system logs.
    :type log: Optional[List[LogConfig]]
    """
    log: Optional[List[LogConfig]] = None
    id: str = field(default_factory=lambda: str(uuid4()))
