from typing import List, Union, Optional, Dict, Any, Type

from cyst.api.environment.configuration import GeneralConfiguration, ObjectType, ConfigurationObjectType
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.host.service import ActiveServiceConfig, PassiveServiceConfig
from cyst.api.configuration.logic.access import AuthorizationConfig
from cyst.api.configuration.logic.data import DataConfig
from cyst.api.configuration.logic.exploit import VulnerableServiceConfig, ExploitParameterConfig, ExploitConfig
from cyst.api.configuration.network.elements import PortConfig, InterfaceConfig, ConnectionConfig
from cyst.api.configuration.network.firewall import FirewallChainConfig, FirewallConfig
from cyst.api.configuration.network.network import NetworkConfig
from cyst.api.configuration.network.router import RouterConfig
from cyst.api.configuration.network.node import NodeConfig
from cyst.api.environment.environment import Environment
from cyst.api.host.service import AccessLevel


# ----------------------------------------------------------------------------------------------------------------------
# Converting configuration description to actual objects
# ----------------------------------------------------------------------------------------------------------------------
class Configurator:
    def __init__(self):
        self._env: Environment
        self._refs: Dict[str, Any] = {}
        self._obj_refs: Dict[str, Any] = {}
        self._connections: List[ConnectionConfig] = []
        self._nodes: List[NodeConfig] = []
        self._routers: List[RouterConfig] = []
        self._active_services: List[ActiveServiceConfig] = []
        self._passive_services: List[PassiveServiceConfig] = []
        self._interfaces: List[InterfaceConfig] = []
        self._authorizations: List[AuthorizationConfig] = []
        self._data: List[DataConfig] = []
        self._exploits: List[ExploitConfig] = []

    def reset(self):
        self._refs.clear()
        self._obj_refs.clear()
        self._connections.clear()
        self._nodes.clear()
        self._routers.clear()
        self._active_services.clear()
        self._passive_services.clear()
        self._interfaces.clear()
        self._authorizations.clear()
        self._data.clear()
        self._exploits.clear()

    # ------------------------------------------------------------------------------------------------------------------
    # All these _process_XXX functions resolve nested members to their id. In the end of the preprocessing, there should
    # be only a flat configuration with ids and no nesting (see members above)
    # ------------------------------------------------------------------------------------------------------------------
    def _process_NetworkConfig(self, cfg: NetworkConfig) -> NetworkConfig:
        node_ids = []
        conn_ids = []

        for node in cfg.nodes:
            if isinstance(node, str):
                node_ids.append(node)
            else:
                node_ids.append(self._process_cfg_item(node))

        for conn in cfg.connections:
            if isinstance(conn, str):
                conn_ids.append(conn)
            else:
                conn_ids.append(self._process_cfg_item(conn))

        cfg.nodes = node_ids
        cfg.connections = conn_ids

        return cfg

    def _process_ConnectionConfig(self, cfg: ConnectionConfig) -> str:
        self._connections.append(cfg)
        self._refs[cfg.id] = cfg
        return cfg.id

    def _process_RouterConfig(self, cfg: RouterConfig):
        interface_ids = []

        for interface in cfg.interfaces:
            if isinstance(interface, str):
                interface_ids.append(interface)
            else:
                interface_ids.append(self._process_cfg_item(interface))

        cfg.interfaces = interface_ids
        self._routers.append(cfg)
        self._refs[cfg.id] = cfg
        return cfg.id

    def _process_NodeConfig(self, cfg: NodeConfig) -> str:
        passive_service_ids = []
        active_service_ids = []
        interface_ids = []

        for service in cfg.passive_services:
            if isinstance(service, str):
                passive_service_ids.append(service)
            else:
                passive_service_ids.append(self._process_cfg_item(service))

        for service in cfg.active_services:
            if isinstance(service, str):
                active_service_ids.append(service)
            else:
                active_service_ids.append(self._process_cfg_item(service))

        for interface in cfg.interfaces:
            if isinstance(interface, str):
                interface_ids.append(interface)
            else:
                interface_ids.append(self._process_cfg_item(interface))

        cfg.passive_services = passive_service_ids
        cfg.active_services = active_service_ids
        cfg.interfaces = interface_ids

        self._nodes.append(cfg)
        self._refs[cfg.id] = cfg

        return cfg.id

    def _process_InterfaceConfig(self, cfg: InterfaceConfig) -> str:
        self._refs[cfg.id] = cfg
        self._interfaces.append(cfg)
        return cfg.id

    def _process_ActiveServiceConfig(self, cfg: ActiveServiceConfig) -> str:
        self._refs[cfg.id] = cfg
        self._active_services.append(cfg)
        return cfg.id

    def _process_PassiveServiceConfig(self, cfg: PassiveServiceConfig) -> str:
        self._refs[cfg.id] = cfg
        self._passive_services.append(cfg)
        
        public_data_ids = []
        private_data_ids = []
        public_auth_ids = []
        private_auth_ids = []
        
        for data in cfg.public_data:
            if isinstance(data, str):
                public_data_ids.append(data)
            else:
                public_data_ids.append(self._process_cfg_item(data))
        
        for data in cfg.private_data:
            if isinstance(data, str):
                private_data_ids.append(data)
            else:
                private_data_ids.append(self._process_cfg_item(data))

        for auth in cfg.public_authorizations:
            if isinstance(auth, str):
                public_auth_ids.append(auth)
            else:
                public_auth_ids.append(self._process_cfg_item(auth))

        for auth in cfg.private_authorizations:
            if isinstance(auth, str):
                private_auth_ids.append(auth)
            else:
                private_auth_ids.append(self._process_cfg_item(auth))
                
        cfg.public_data = public_data_ids
        cfg.private_data = private_data_ids
        cfg.public_authorizations = public_auth_ids
        cfg.private_authorizations =private_auth_ids
        
        return cfg.id

    def _process_AuthorizationConfig(self, cfg: AuthorizationConfig) -> str:
        self._refs[cfg.id] = cfg
        self._authorizations.append(cfg)
        return cfg.id

    def _process_DataConfig(self, cfg: DataConfig) -> str:
        self._refs[cfg.id] = cfg
        self._data.append(cfg)
        return cfg.id

    def _process_ExploitConfig(self, cfg: ExploitConfig) -> str:
        self._refs[cfg.id] = cfg
        self._exploits.append(cfg)
        return cfg.id

    def _process_default(self, cfg):
        raise ValueError("Unknown config type provided")

    def _process_cfg_item(self, cfg: Any) -> str:
        if hasattr(cfg, "id") and cfg.id in self._refs:
            raise ValueError("Duplicate identifier found: {}".format(cfg.id))

        fn = getattr(self, "_process_" + type(cfg).__name__, self._process_default)
        return fn(cfg)

    def get_configuration_by_id(self, id: str) -> Optional[Any]:
        if id not in self._refs:
            return None
        else:
            return self._refs[id]

    def get_object_by_id(self, id: str) -> Optional[Any]:
        if id not in self._obj_refs:
            return None
        else:
            return self._obj_refs[id]

    # ------------------------------------------------------------------------------------------------------------------
    # Gather all configuration items
    # TODO: Return of Environment is an artifact of previous development. Need to change it to something more useful
    def configure(self, env: Optional[Environment], *configs: Union[NetworkConfig, ConnectionConfig, RouterConfig, NodeConfig,
                                                                    InterfaceConfig, ActiveServiceConfig, PassiveServiceConfig,
                                                                    AuthorizationConfig, DataConfig]) -> Environment:
        if not env:
            self._env = Environment.create()
        else:
            self._env = env
            # Everytime a configuration of environment is required, there must be a complete reset of it
            env.control.reset()

        # --------------------------------------------------------------------------------------------------------------
        # Process all provided items and do a complete id->cfg mapping
        for cfg in configs:
            self._process_cfg_item(cfg)

        # --------------------------------------------------------------------------------------------------------------
        # Now that each configuration item is accounted for, build it.
        # Build order:
        # 1) Authorizations, Data and Exploits
        # 2) Passive Services
        # 3) Interfaces
        # 4) Nodes and routers
        # 5) Connections

        # 1) Authorizations, Data and Exploits
        for auth in self._authorizations:
            a = self._env.policy.create_authorization(auth.identity, auth.nodes, auth.services, auth.access_level, auth.id)
            self._env.policy.add_authorization(a)
            self._obj_refs[auth.id] = a

        for data in self._data:
            d = self._env.configuration.service.create_data(data.id, data.owner, data.description)
            self._obj_refs[data.id] = d

        for exploit in self._exploits:
            params = []
            if exploit.parameters:
                for p in exploit.parameters:
                    param = self._env.configuration.exploit.create_exploit_parameter(p.type, p.value, p.immutable)
                    params.append(param)

            services = []
            for s in exploit.services:
                service = self._env.configuration.exploit.create_vulnerable_service(s.name, s.min_version, s.max_version)
                services.append(service)

            e = self._env.configuration.exploit.create_exploit(exploit.id, services, exploit.locality, exploit.category, *params)

            self._env.configuration.exploit.add_exploit(e)

        # 2) Passive Services
        passive_service_obj = {}
        for service in self._passive_services:
            s = self._env.configuration.service.create_passive_service(service.type, service.owner, service.version, service.local, service.access_level)

            for d in service.public_data:
                self._env.configuration.service.public_data(s.passive_service).append(self._obj_refs[d])
            for d in service.private_data:
                self._env.configuration.service.private_data(s.passive_service).append(self._obj_refs[d])
            for a in service.public_authorizations:
                self._env.configuration.service.public_authorizations(s.passive_service).append(self._obj_refs[a])
            for a in service.private_authorizations:
                self._env.configuration.service.private_authorizations(s.passive_service).append(self._obj_refs[a])

            for p in service.parameters:
                self._env.configuration.service.set_service_parameter(s.passive_service, p[0], p[1])

            passive_service_obj[service.id] = s
            self._obj_refs[service.id] = s

        # 3) Interfaces
        for iface in self._interfaces:
            # TODO: Missing a setting of a gateway (Really todo?)
            i = self._env.configuration.node.create_interface(iface.ip, str(iface.net.netmask), iface.index)
            self._obj_refs[iface.id] = i

        # 4) Nodes
        for node in self._nodes:
            n = self._env.configuration.node.create_node(node.id)
            for i in node.interfaces:
                obj_i = self._obj_refs[i]
                self._env.configuration.node.add_interface(n, obj_i, obj_i.index)

            for service in node.passive_services:
                self._env.configuration.node.add_service(n, passive_service_obj[service])

            for service in node.active_services:
                service_cfg: ActiveServiceConfig = self._refs[service]
                s = self._env.configuration.service.create_active_service(service_cfg.type, service_cfg.owner, service_cfg.name, n, service_cfg.access_level, service_cfg.configuration)
                self._obj_refs[service_cfg.id] = s
                self._env.configuration.node.add_service(n, s)

            self._env.configuration.network.add_node(n)

            self._obj_refs[node.id] = n

        for router in self._routers:
            r = self._env.configuration.node.create_router(router.id, self._env.messaging)
            for iface_id in router.interfaces:
                iface = self._obj_refs[iface_id]
                self._env.configuration.node.add_interface(r, iface, iface.index)
            self._env.configuration.network.add_node(r)

            self._obj_refs[router.id] = r

        # 5) Connections
        for conn in self._connections:
            src = self._obj_refs[conn.src_id]
            dst = self._obj_refs[conn.dst_id]

            self._env.configuration.network.add_connection(src, dst, conn.src_port, conn.dst_port)

        return self._env


# ----------------------------------------------------------------------------------------------------------------------
class Configuration(GeneralConfiguration):

    def __init__(self, env: Environment) -> None:
        self._env = env
        self._configurator = Configurator()

    def configure(self, *config_item: Union[NetworkConfig, ConnectionConfig, RouterConfig, NodeConfig,
                                            InterfaceConfig, ActiveServiceConfig, PassiveServiceConfig,
                                            AuthorizationConfig, DataConfig]) -> Environment:
        self._configurator.reset()
        self._configurator.configure(self._env, *config_item)
        return self._env

    def get_configuration_by_id(self, id: str,
                                configuration_type: Type[ConfigurationObjectType]) -> ConfigurationObjectType:

        c = self._configurator.get_configuration_by_id(id)
        if not isinstance(c, configuration_type):
            raise AttributeError("Attempting to cast configuration object with id: {} to an incompatible type: {}".format(id, str(configuration_type)))
        return c

    def get_object_by_id(self, id: str, object_type: Type[ObjectType]) -> ObjectType:

        o = self._configurator.get_object_by_id(id)
        if not isinstance(o, object_type):
            raise AttributeError(
                "Attempting to cast object with id: {} to an incompatible type: {}".format(id, str(object_type)))
        return o
