from __future__ import annotations

from typing import List, Any

from cyst.api.environment.configuration import ActionConfiguration
from cyst.api.logic.action import ActionParameterDomain

from cyst.core.logic.action import ActionParameterDomainImpl


class ActionConfigurationImpl(ActionConfiguration):

    def create_action_parameter_domain_any(self) -> ActionParameterDomain:
        return ActionParameterDomainImpl()

    def create_action_parameter_domain_range(self, default: int, min: int, max: int,
                                             step: int = 1) -> ActionParameterDomain:
        return ActionParameterDomainImpl.bind_range(default, min, max, step)

    def create_action_parameter_domain_options(self, default: Any, options: List[Any]) -> ActionParameterDomain:
        return ActionParameterDomainImpl.bind_options(default, options)
