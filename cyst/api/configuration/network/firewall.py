from dataclasses import dataclass, field
from typing import List
from uuid import uuid4
from tools.serde_customized import serialize, deserialize

from cyst.api.configuration.configuration import ConfigItem
from cyst.api.network.firewall import FirewallRule, FirewallChainType, FirewallPolicy


@deserialize
@serialize
@dataclass
class FirewallChainConfig(ConfigItem):
    type: FirewallChainType
    policy: FirewallPolicy
    rules: List[FirewallRule]
    id: str = field(default_factory=lambda: str(uuid4()))


@deserialize
@serialize
@dataclass
class FirewallConfig(ConfigItem):
    default_policy: FirewallPolicy
    chains: List[FirewallChainConfig]
    id: str = field(default_factory=lambda: str(uuid4()))
