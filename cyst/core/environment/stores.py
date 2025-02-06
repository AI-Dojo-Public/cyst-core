import builtins

from copy import deepcopy
from typing import List, Optional, Dict, Union, Tuple, Any

from cyst.api.environment.configuration import RuntimeConfiguration
from cyst.api.environment.environment import EnvironmentMessaging
from cyst.api.environment.message import Message
from cyst.api.environment.stores import ActionStore, ExploitStore, ServiceStore
from cyst.api.environment.platform_specification import PlatformSpecification, PlatformType
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.logic.access import AccessLevel
from cyst.api.logic.action import ActionDescription, Action
from cyst.api.logic.exploit import Exploit, ExploitCategory, ExploitLocality
from cyst.api.host.service import PassiveService, ActiveServiceDescription, ActiveService
from cyst.api.network.node import Node

from cyst.core.logic.action import ActionImpl
# from cyst.core.host.service import ServiceImpl
# from cyst.core.network.session import SessionImpl
# from cyst.core.network.node import NodeImpl


class ServiceStoreImpl(ServiceStore):

    def __init__(self, messaging: EnvironmentMessaging, resources: EnvironmentResources, runtime_configuration: RuntimeConfiguration):
        self._services = {}
        self._messaging = messaging
        self._resources = resources
        self._runtime_configuration = runtime_configuration

        self._service_instances = {}
        self._service_instance_ids = {}

    def add_service(self, description: ActiveServiceDescription) -> None:
        self._services[description.name] = description

    def get_service(self, name: str) -> Optional[ActiveServiceDescription]:
        if name in self._services:
            return self._services[name]
        else:
            return None

    def create_active_service(self, type: str, owner: str, name: str, node: Node,
                              service_access_level: AccessLevel = AccessLevel.LIMITED,
                              configuration: Optional[Dict[str, Any]] = None, id: str = "") -> Optional[ActiveService]:
        if not type in self._services:
            raise RuntimeError(f"Attempting to create nonexistent service {type}.")
        service_description: ActiveServiceDescription = self._services[type]

        # Configuration is extended by parameters that are passed through the runtime configuration mechanism.
        # The runtime configuration takes precedence over what is inside the configuration file.
        if not configuration:
            configuration = {}

        configuration.update(self._runtime_configuration.other_params)

        service = service_description.creation_fn(self._messaging, self._resources, id, configuration)
        #return ServiceImpl(type, service, name, owner, service_access_level, id)

        # service is stored according to its in-engine ID as well as its address to help with message sending
        self._service_instances[id] = service
        self._service_instance_ids[builtins.id(service)] = id

        return service

    def get_active_service(self, id) -> Optional[ActiveService]:
        return self._service_instances[id]


    def get_active_services(self) -> List[ActiveService]:
        return list(self._service_instances.values())

    def get_active_service_id(self, address: str) -> str:
        return self._service_instance_ids[address]

class ActionStoreImpl(ActionStore):

    def __init__(self, platform: Optional[PlatformSpecification] = None):
        self._actions = {}
        if platform:
            self._platform = platform
        else:
            self._platform = PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST")

    def get(self, id: str = "") -> Optional[Action]:
        if id in self._actions:
            return deepcopy(self._actions[id])
        return None

    def get_ref(self, id: str = "") -> Optional[Action]:
        if id in self._actions:
            return self._actions[id]
        return None

    def get_prefixed(self, prefix: str = "") -> List[Action]:
        result = []
        for id, value in self._actions.items():
            if id.startswith(prefix):
                result.append(deepcopy(value))
        return result

    def add(self, action: ActionDescription) -> None:
        action_platform = action.platform

        if not action_platform:
            action_platform = PlatformSpecification(PlatformType.SIMULATED_TIME, "CYST")

        if type(action_platform) != list:
            action_platform = [action_platform]

        if not self._platform in action_platform:
            return

        if action.id in self._actions:
            raise RuntimeError(f"Attempting to add action with ID that is already present for platform {self._platform}: {action.id}")
        self._actions[action.id] = ActionImpl(action)


class ExploitStoreImpl(ExploitStore):
    def __init__(self):
        # Nested lists here are to allow easier conversion to sets and to do the intersection
        # TODO: revise the data structure logic here
        self._by_id: Dict[str, List[Exploit]] = {}
        self._by_service: Dict[str, List[Exploit]] = {}
        self._by_category: Dict[ExploitCategory, List[Exploit]] = {}

    def clear(self) -> None:
        self._by_id.clear()
        self._by_service.clear()
        self._by_category.clear()

    def add_exploit(self, *exploits: Exploit) -> None:
        for exploit in exploits:
            # Exploit already in store, do nothing
            if exploit.id in self._by_id:
                return

            self._by_id[exploit.id] = [exploit]

            for service in exploit.services.values():
                if service.id not in self._by_service:
                    self._by_service[service.id] = []

                self._by_service[service.id].append(exploit)

            if exploit.category not in self._by_category:
                self._by_category[exploit.category] = []

            self._by_category[exploit.category].append(exploit)

    def get_exploit(self, id: str = "", service: str = "", category: ExploitCategory = ExploitCategory.NONE) -> Optional[List[Exploit]]:
        candidate_sets = []

        if id:
            candidate_sets.append(set(self._by_id.get(id, [])))

        if service:
            candidate_sets.append(set(self._by_service.get(service, [])))

        if category != ExploitCategory.NONE:
            candidate_sets.append(set(self._by_category.get(category, [])))

        if not candidate_sets:
            return []
        else:
            return list(set.intersection(*candidate_sets))

    def evaluate_exploit(self, exploit: Union[str, Exploit], message: Message, node: Node) -> Tuple[bool, str]:
        if isinstance(exploit, str):
            exploits = self.get_exploit(exploit)
            if not exploits:
                return False, "Could not find exploit by id"
            else:
                # Gah!
                exploit = exploits[0]

        # For exploit to be applicable, a number of conditions must be satisfied.
        # 1) Local exploits can only be used at the session end
        if exploit.locality == ExploitLocality.LOCAL:
            if not message.session:
                return False, "Local exploits can only be used from within an existing session"
            elif not message.session.end[0] in [iface.ip for iface in node.interfaces]:
                return False, "Local exploits can only be used at session endpoint."

        # 2) Exploits must be applicable on given service_id
        exploit_service = exploit.services.get(message.dst_service, None)
        if not exploit_service:
            return False, "Attempting to use exploit on a service it does not apply to"

        # 3) service_id must exist on node
        node_service = node.services.get(message.dst_service, None)
        if not node_service:
            return False, "The exploit is not fit for any of the services on the node"

        # 4) Versions must match
        if isinstance(node_service, PassiveService) and not exploit_service.min_version <= node_service.version <= exploit_service.max_version:
            return False, "The exploit is not applicable on the current version of a service"

        # 5) TODO There will also be tags to evaluate, but that is a future endeavour

        return True, ""

    @staticmethod
    def cast_from(o: ExploitStore) -> 'ExploitStoreImpl':
        if isinstance(o, ExploitStoreImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the ExploitStore interface")
