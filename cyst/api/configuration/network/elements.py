from dataclasses import dataclass, field
from netaddr import IPAddress, IPNetwork
from typing import Optional
from uuid import uuid4
from tools.serde_customized import serialize

from cyst.api.configuration.configuration import ConfigItem


@serialize
@dataclass
class PortConfig(ConfigItem):
    ip: IPAddress = field(metadata={
        'serde_serializer': lambda x: str(x),
        'serde_deserializer': lambda x: IPAddress(x)
    })
    net: IPNetwork = field(metadata={
        'serde_serializer': lambda x: str(x),
        'serde_deserializer': lambda x: IPNetwork(x)
    })
    index: int = field(default=-1)
    id: str = field(default_factory=lambda: str(uuid4()))


@serialize
@dataclass
class InterfaceConfig(ConfigItem):
    ip: IPAddress = field(metadata={
        'serde_serializer': lambda x: str(x),
        'serde_deserializer': lambda x: IPAddress(x)
    })
    net: IPNetwork = field(metadata={
        'serde_serializer': lambda x: str(x),
        'serde_deserializer': lambda x: IPNetwork(x)
    })
    index: int = field(default=-1)
    id: str = field(default_factory=lambda: str(uuid4()))


@serialize
@dataclass
class ConnectionConfig(ConfigItem):
    src_id: str
    src_port: int
    dst_id: str
    dst_port: int
    id: str = field(default_factory=lambda: str(uuid4()))
