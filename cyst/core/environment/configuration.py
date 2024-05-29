import jsonpickle
import logging.config
import uuid

from dataclasses import dataclass, field
from typing import Dict, List, Union, Any, Callable, Optional, Type

import netaddr

from cyst.api.environment.configuration import GeneralConfiguration, ObjectType, ConfigurationObjectType
from cyst.api.environment.environment import Environment
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.host.service import ActiveServiceConfig, PassiveServiceConfig
from cyst.api.configuration.infrastructure.infrastructure import InfrastructureConfig
from cyst.api.configuration.infrastructure.log import LogConfig, LogSource, log_defaults
from cyst.api.configuration.logic.access import AuthorizationConfig, AuthenticationProviderConfig, AccessSchemeConfig, \
    AuthorizationDomainConfig, FederatedAuthorizationConfig
from cyst.api.configuration.logic.data import DataConfig
from cyst.api.configuration.logic.exploit import VulnerableServiceConfig, ExploitParameterConfig, ExploitConfig
from cyst.api.configuration.network.elements import PortConfig, InterfaceConfig, ConnectionConfig, RouteConfig
from cyst.api.configuration.network.firewall import FirewallChainConfig, FirewallConfig, FirewallPolicy, FirewallChainType
from cyst.api.configuration.network.network import NetworkConfig
from cyst.api.configuration.network.router import RouterConfig
from cyst.api.configuration.network.node import NodeConfig


class Configurator:
    def __init__(self):
        self._refs: Dict[str, Any] = {}
        self._connections: List[ConnectionConfig] = []
        self._nodes: List[NodeConfig] = []
        self._routers: List[RouterConfig] = []
        self._active_services: List[ActiveServiceConfig] = []
        self._passive_services: List[PassiveServiceConfig] = []
        self._firewalls: List[FirewallConfig] = []
        self._interfaces: List[Union[InterfaceConfig, PortConfig]] = []
        self._authorizations: List[AuthorizationConfig] = []
        self._data: List[DataConfig] = []
        self._exploits: List[ExploitConfig] = []
        self._authentication_providers: List[AuthenticationProviderConfig] = []
        self._access_schemes: List[AccessSchemeConfig] = []
        self._authorization_domains: List[AuthorizationDomainConfig] = []
        self._logs: List[LogConfig] = []

    def __getstate__(self):
        result = self.__dict__
        return result

    def __setstate__(self, state):
        self.__dict__.update(state)

    def reset(self):
        self._refs.clear()
        self._connections.clear()
        self._nodes.clear()
        self._routers.clear()
        self._active_services.clear()
        self._passive_services.clear()
        self._firewalls.clear()
        self._interfaces.clear()
        self._authorizations.clear()
        self._data.clear()
        self._exploits.clear()
        self._authentication_providers.clear()
        self._access_schemes.clear()
        self._authorization_domains.clear()
        self._logs.clear()

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
        traffic_processor_ids = []
        route_ids = []

        for interface in cfg.interfaces:
            if isinstance(interface, str):
                interface_ids.append(interface)
            else:
                interface_ids.append(self._process_cfg_item(interface))

        for processor in cfg.traffic_processors:
            if isinstance(processor, str):
                traffic_processor_ids.append(processor)
            else:
                traffic_processor_ids.append(self._process_cfg_item(processor))

        for route in cfg.routing_table:
            self._process_RouteConfig(route)

        cfg.interfaces = interface_ids
        cfg.traffic_processors = traffic_processor_ids

        self._routers.append(cfg)
        self._refs[cfg.id] = cfg
        return cfg.id

    def _process_NodeConfig(self, cfg: NodeConfig) -> str:
        passive_service_ids = []
        active_service_ids = []
        traffic_processor_ids = []
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

        for processor in cfg.traffic_processors:
            if isinstance(processor, str):
                traffic_processor_ids.append(processor)
            else:
                traffic_processor_ids.append(self._process_cfg_item(processor))

        for interface in cfg.interfaces:
            if isinstance(interface, str):
                interface_ids.append(interface)
            else:
                interface_ids.append(self._process_cfg_item(interface))

        cfg.passive_services = passive_service_ids
        cfg.active_services = active_service_ids
        cfg.traffic_processors = traffic_processor_ids
        cfg.interfaces = interface_ids

        self._nodes.append(cfg)
        self._refs[cfg.id] = cfg

        return cfg.id

    def _process_PortConfig(self, cfg: PortConfig) -> str:
        self._refs[cfg.id] = cfg
        self._interfaces.append(cfg)
        return cfg.id

    def _process_InterfaceConfig(self, cfg: InterfaceConfig) -> str:
        self._refs[cfg.id] = cfg
        self._interfaces.append(cfg)
        return cfg.id

    def _process_ActiveServiceConfig(self, cfg: ActiveServiceConfig) -> str:
        self._refs[cfg.id] = cfg
        self._active_services.append(cfg)
        return cfg.id

    def _process_FirewallConfig(self, cfg: FirewallConfig) -> str:
        self._refs[cfg.id] = cfg
        self._firewalls.append(cfg)
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
        cfg.private_authorizations = private_auth_ids

        auth_provider_ids = []
        for provider in cfg.authentication_providers:
            if isinstance(provider, str):
                auth_provider_ids.append(provider)
            else:
                auth_provider_ids.append(self._process_cfg_item(provider))
        cfg.authentication_providers = auth_provider_ids

        access_scheme_ids = []
        for scheme in cfg.access_schemes:
            if isinstance(scheme, str):
                access_scheme_ids.append(scheme)
            else:
                access_scheme_ids.append(self._process_cfg_item(scheme))
        cfg.access_schemes = access_scheme_ids

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

    def _process_AuthenticationProviderConfig(self, cfg: AuthenticationProviderConfig) -> str:
        self._refs[cfg.id] = cfg
        self._authentication_providers.append(cfg)
        return cfg.id

    def _process_AccessSchemeConfig(self, cfg: AccessSchemeConfig) -> str:

        auth_provider_ids = []
        for provider in cfg.authentication_providers:
            if isinstance(provider, str):
                auth_provider_ids.append(provider)
            else:
                auth_provider_ids.append(self._process_cfg_item(provider))
        cfg.authentication_providers = auth_provider_ids

        if not isinstance(cfg.authorization_domain, str):
            cfg.authorization_domain = self._process_cfg_item(cfg.authorization_domain)

        self._refs[cfg.id] = cfg
        self._access_schemes.append(cfg)
        return cfg.id

    def _process_AuthorizationDomainConfig(self, cfg: AuthorizationDomainConfig) -> str:

        authorization_ids = []
        for auth in cfg.authorizations:
            if isinstance(auth, str):
                authorization_ids.append(auth)
            else:
                authorization_ids.append(self._process_cfg_item(auth))
        cfg.authorizations = authorization_ids

        self._refs[cfg.id] = cfg
        self._authorization_domains.append(cfg)
        return cfg.id

    def _process_FederatedAuthorizationConfig(self, cfg: FederatedAuthorizationConfig):

        # TODO : Ask how this is meant to be handled

        self._refs[cfg.id] = cfg
        return cfg.id

    def _process_RouteConfig(self, cfg: RouteConfig) -> str:

        self._refs[cfg.id] = cfg
        return cfg.id

    def _process_LogConfig(self, cfg: LogConfig) -> str:
        self._refs[cfg.id] = cfg
        self._logs.append(cfg)
        return cfg.id

    def _process_InfrastructureConfig(self, cfg: InfrastructureConfig) -> str:
        self._refs[cfg.id] = cfg
        for log in cfg.log:
            self._process_LogConfig(log)
        return cfg.id

    def _process_default(self, cfg):
        raise ValueError("Unknown config type provided")

    def _process_cfg_item(self, cfg: Any) -> str:
        if hasattr(cfg, "id") and cfg.id in self._refs:
            if self._refs[cfg.id] != cfg:
                raise ValueError("Duplicate identifier for different configuration objects found: {}".format(cfg.id))
            else:
                return cfg.id
        else:
            fn: Callable[[ConfigItem], str] = getattr(self, "_process_" + type(cfg).__name__, self._process_default)
            return fn(cfg)

    # ------------------------------------------------------------------------------------------------------------------
    def preprocess(self,
                  *configs: Union[NetworkConfig, ConnectionConfig, RouterConfig, NodeConfig,
                                  InterfaceConfig, ActiveServiceConfig, PassiveServiceConfig,
                                  AuthorizationConfig, DataConfig]) -> 'Configurator':

        # --------------------------------------------------------------------------------------------------------------
        # Process all provided items and do a complete id->cfg mapping
        for cfg in configs:
            self._process_cfg_item(cfg)

        # Create interface configurations for connections with one -1 port id
        for connection_cfg in self._connections:
            if connection_cfg.dst_port == -1 or connection_cfg.src_port == -1:
                if connection_cfg.dst_port == -1:
                    target_id = connection_cfg.dst_id
                    source_id = connection_cfg.src_id
                    source_port = connection_cfg.src_port
                else:
                    target_id = connection_cfg.src_id
                    source_id = connection_cfg.dst_id
                    source_port = connection_cfg.dst_port

                target_config = self._refs[target_id]
                source_config = self._refs[source_id]

                new_interface_index = len(target_config.interfaces)
                new_interface_id = str(uuid.uuid4())

                source_net = self._refs[source_config.interfaces[source_port]].net

                # The port is on the leaf, use the first free address from the router
                if isinstance(target_config, NodeConfig):
                    allocated_ips = []

                    # The following is not pretty and not optimal, however...
                    # Get all nodes connected to the same router we are trying to connect to now
                    connected_ids = []
                    for conn in self._connections:
                        if source_config.id == conn.src_id:
                            connected_ids.append(conn.dst_id)
                        elif source_config.id == conn.dst_id:
                            connected_ids.append(conn.src_id)

                    for node_cfg in self._nodes:
                        if node_cfg.id in connected_ids:
                            for iface_id in node_cfg.interfaces:
                                iface_cfg = self._refs[iface_id]
                                allocated_ips.append(iface_cfg.ip)

                    # Add router addresses
                    for iface in source_config.interfaces:
                        allocated_ips.append(self._refs[iface].ip)

                    new_ip = None
                    for ip in source_net.iter_hosts():
                        if ip not in allocated_ips:
                            new_ip = ip
                            break

                    if not new_ip:
                        raise RuntimeError(f"Cannot find a free IP for target in a connection {connection_cfg}.")

                    iface = InterfaceConfig(
                        ip = new_ip,
                        net = source_net,
                        index = new_interface_index,
                        id = new_interface_id
                    )

                # The port is on the router, just copy the configuration from the leaf node
                elif isinstance(target_config, RouterConfig):
                    # Set the IP to the first address in the net
                    iface = InterfaceConfig(
                        ip=netaddr.IPAddress(source_net.first + 1),
                        net=source_net,
                        index=new_interface_index,
                        id=new_interface_id
                    )

                else:
                    raise RuntimeError(f"Attempting to connect something else than a node or router: {target_config}.")

                self._interfaces.append(iface)
                self._refs[new_interface_id] = iface
                target_config.interfaces.append(new_interface_id)

                if connection_cfg.dst_port == -1:
                    connection_cfg.dst_port = new_interface_index
                else:
                    connection_cfg.src_port = new_interface_index

        return self

    # ------------------------------------------------------------------------------------------------------------------
    # Configuration of global stuff that is not relegated to platforms
    def configure(self):

        # --------------------------------------------------------------------------------------------------------------
        # Logs:
        # Get defaults
        log_configs = {}
        for log in log_defaults:
            log_configs[log.source] = log

        # Overwrite with user configuration
        for cfg in self._logs:
            log_configs[cfg.source] = cfg

        formatters = {
            '__default': {
                'format': "[%(asctime)s] :: %(name)s — %(levelname)s :: %(message)s"
            }
        }

        handlers = {}
        loggers = {}

        log_source_map = {
            LogSource.SYSTEM: 'system',
            LogSource.MESSAGING: 'messaging',
            LogSource.MODEL: 'model.',
            LogSource.SERVICE: 'service.'
        }

        for cfg in log_configs.values():
            if not cfg.log_console and not cfg.log_file:
                continue

            handler_console = {}
            handler_file = {}

            if cfg.log_console:
                handler_console = {
                    'class': 'logging.StreamHandler',
                    'formatter': '__default',
                    'level': cfg.log_level,
                    'stream': 'ext://sys.stdout'
                }

            if cfg.log_file and cfg.file_path:
                handler_file = {
                    'class': 'logging.FileHandler',
                    'formatter': '__default',
                    'level': cfg.log_level,
                    'filename': cfg.file_path
                }

            if handler_console or handler_file:
                handler_list = []
                if handler_console:
                    id = "__console_" + log_source_map[cfg.source]
                    handlers[id] = handler_console
                    handler_list.append(id)
                if handler_file:
                    id = "__file_" + log_source_map[cfg.source]
                    handlers[id] = handler_file
                    handler_list.append(id)

                loggers[log_source_map[cfg.source]] = {
                    'handlers': handler_list,
                    'level': cfg.log_level
                }

        log_config_dict = {
            'version': 1,
            'formatters': formatters,
            'handlers': handlers,
            'loggers': loggers
        }

        logging.config.dictConfig(log_config_dict)

    def get_configuration_by_id(self, id: str) -> Optional[Any]:
        if id not in self._refs:
            return None
        else:
            return self._refs[id]

    def _resolve_config_item(self, item: ConfigItem) -> ConfigItem:
        replaced = {}
        for key, value in item.__dict__.items():
            if isinstance(value, str) and not key.endswith("id") and value in self._refs:
                replaced[key] = self._resolve_config_item(self._refs[value])
            if isinstance(value, list):
                tmp = []
                for element in value:
                    if isinstance(element, str) and element in self._refs:
                        tmp.append(self._resolve_config_item(self._refs[element]))
                if tmp:
                    replaced[key] = tmp
        item.__dict__.update(replaced)
        return item

    def get_configuration(self) -> List[ConfigItem]:
        top_level = [*self._nodes, *self._routers, *self._connections, *self._exploits]
        result = []
        for item in top_level:
            result.append(self._resolve_config_item(item))
        return result


# ----------------------------------------------------------------------------------------------------------------------
class GeneralConfigurationImpl(GeneralConfiguration):

    def __init__(self, env: Environment) -> None:
        self._configurator = Configurator()
        self._env = env

    def preprocess(self, *config) -> None:
        self._configurator.preprocess(*config)

    def configure(self) -> None:
        self._configurator.configure()

    def get_configuration(self) -> List[ConfigItem]:
        return self._configurator.get_configuration()

    def save_configuration(self, indent: Optional[int]) -> str:
        return jsonpickle.encode(self._configurator.get_configuration(), make_refs=False, indent=indent)

    def load_configuration(self, config: str) -> List[ConfigItem]:
        return jsonpickle.decode(config)

    def get_configuration_by_id(self, id: str,
                                configuration_type: Type[ConfigurationObjectType]) -> ConfigurationObjectType:

        c = self._configurator.get_configuration_by_id(id)
        if not isinstance(c, configuration_type):
            raise AttributeError(
                "Attempting to cast configuration object with id: {} to an incompatible type: {}".format(id,
                                                                                                         str(configuration_type)))
        return c

    def get_object_by_id(self, id: str, object_type: Type[ObjectType]) -> ObjectType:
        if self._env.platform:
            return self._env.platform.configuration.general.get_object_by_id(id, object_type)

    @staticmethod
    def cast_from(o: GeneralConfiguration) -> 'GeneralConfigurationImpl':
        if isinstance(o, GeneralConfigurationImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the GeneralConfiguration interface")
