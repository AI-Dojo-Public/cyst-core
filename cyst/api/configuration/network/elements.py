from dataclasses import dataclass, field
from netaddr import IPAddress, IPNetwork
from typing import Optional
from uuid import uuid4

from cyst.api.configuration.configuration import ConfigItem


@dataclass
class PortConfig(ConfigItem):
    ip: IPAddress
    net: IPNetwork
    index: int = field(default=-1)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class InterfaceConfig(ConfigItem):
    ip: IPAddress
    net: IPNetwork
    index: int = field(default=-1)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ConnectionConfig(ConfigItem):
    src_id: str
    src_port: int
    dst_id: str
    dst_port: int
    id: str = field(default_factory=lambda: str(uuid4()))
