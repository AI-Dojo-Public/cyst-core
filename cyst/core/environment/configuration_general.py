import logging.config
import uuid
import collections

from dataclasses import dataclass, field
from typing import List, Union, Optional, Dict, Any, Type, Tuple, Callable

import jsonpickle

from cyst.api.environment.configuration import GeneralConfiguration, ObjectType, ConfigurationObjectType
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
from cyst.api.environment.environment import Environment
from cyst.api.host.service import AccessLevel
from cyst.api.network.node import Node

from cyst.core.network.firewall import FirewallImpl
from cyst.core.network.elements import ConnectionImpl
from cyst.core.network.node import NodeImpl


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
        self._obj_refs.clear()
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

    def get_objects_by_type(self, type: Type[ObjectType]) -> List[ObjectType]:
        result = []
        for obj in self._obj_refs.values():
            if isinstance(obj, type):
                result.append(obj)
        return result

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

    def add_object(self, id: str, obj: Any) -> None:
        if id in self._obj_refs:
            tmp = self._obj_refs[id]
            raise RuntimeError(f"Attempting to add an already existing object with id: {id} and type: {type(tmp)}")

        self._obj_refs[id] = obj

    # ------------------------------------------------------------------------------------------------------------------
    # Gather all configuration items
    # TODO: Return of Environment is an artifact of previous development. Need to change it to something more useful
    def configure(self, env: Optional[Environment],
                  *configs: Union[NetworkConfig, ConnectionConfig, RouterConfig, NodeConfig,
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
        # Begin by processing the infrastructure configuration
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

        # --------------------------------------------------------------------------------------------------------------
        # Now that each configuration item is accounted for, build it.
        # Build order:
        # 1) Authorizations, Data and Exploits
        # 2) Passive Services
        # 3) Interfaces
        # 4) Nodes and routers
        # 5) Connections

        # 1) Authorizations, Data and Exploits
        # for auth in self._authorizations:
        #    a = self._env.policy.create_authorization(auth.identity, auth.nodes, auth.services, auth.access_level, auth.id)
        #    self._env.policy.add_authorization(a)
        #    self._obj_refs[auth.id] = a

        # Building authentication and authorization infrastructure
        # Prepare authentication tokens based on the authorizations in access schemes
        for scheme in self._access_schemes:

            scheme_instance = self._env.configuration.access.create_access_scheme(scheme.id)

            authorization_domain = self._refs[scheme.authorization_domain]

            # Go through all providers and if they do not exist instantiate them
            for provider_id in scheme.authentication_providers:
                provider_conf: AuthenticationProviderConfig = self._refs[provider_id]

                if provider_id not in self._obj_refs:
                    provider = self._env.configuration.access.create_authentication_provider(
                        provider_conf.provider_type,
                        provider_conf.token_type,
                        provider_conf.token_security,
                        provider_conf.ip,
                        provider_conf.timeout,
                        provider_id
                    )
                else:
                    provider = self._obj_refs[provider_id]

                self._env.configuration.access.add_provider_to_scheme(provider, scheme_instance)

            for auth_id in authorization_domain.authorizations:
                auth = self._refs[auth_id]
                if isinstance(auth, AuthorizationConfig) or isinstance(auth, FederatedAuthorizationConfig):
                    identity = auth.identity

                    # This is not very pretty, but the original version that ran this code for each provider caused
                    # problems with the new approach that correctly tracks IDs of objects. In this case objects with
                    # identical IDs could be created multiple times.
                    for provider_id in scheme.authentication_providers:
                        self._env.configuration.access.create_and_register_authentication_token(self._obj_refs[provider_id], identity)

                    # WARN: this creates authorizations with services = ["*"], nodes = ["*"] if not Federated is
                    # created, when the authorization process is
                    # done, these are only used as templates so should not be a problem
                    authorization = self._env.configuration.access.create_authorization(auth.identity,
                                                                                        auth.access_level, auth.id)\
                        if not isinstance(auth, FederatedAuthorizationConfig) else \
                        self._env.configuration.access.create_authorization(auth.identity, auth.access_level,
                                                                            auth.id, auth.nodes, auth.services)

                    self._env.configuration.access.add_authorization_to_scheme(authorization, scheme_instance)
                else:
                    raise RuntimeError("Wrong object type provided instead of (Federated)AuthorizationConfig")

        for data in self._data:
            d = self._env.configuration.service.create_data(data.id, data.owner, data.description)

        for exploit in self._exploits:
            params = []
            if exploit.parameters:
                for p in exploit.parameters:
                    param = self._env.configuration.exploit.create_exploit_parameter(p.type, p.value, p.immutable)
                    params.append(param)

            services = []
            for s in exploit.services:
                service = self._env.configuration.exploit.create_vulnerable_service(s.name, s.min_version,
                                                                                    s.max_version)
                services.append(service)

            e = self._env.configuration.exploit.create_exploit(exploit.id, services, exploit.locality, exploit.category,
                                                               *params)

            self._env.configuration.exploit.add_exploit(e)

        # 2) Passive Services
        passive_service_obj = {}
        for service in self._passive_services:
            s = self._env.configuration.service.create_passive_service(service.type, service.owner, service.version,
                                                                       service.local, service.access_level, service.id)

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

            for prov in service.authentication_providers:
                self._env.configuration.service.provides_auth(s,
                                                              self._obj_refs[prov.id if isinstance(prov,
                                                                            AuthenticationProviderConfig) else prov])

            for scheme in service.access_schemes:
                self._env.configuration.service.set_scheme(s, self._obj_refs[
                    scheme.id if isinstance(scheme, AccessSchemeConfig) else scheme])

            passive_service_obj[service.id] = s

        # 3) Interfaces
        for iface in self._interfaces:
            if isinstance(iface, PortConfig):
                self._env.configuration.node.create_port(iface.ip, str(iface.net.netmask), iface.index, iface.id)
            else:
                # TODO: Missing a setting of a gateway (Really todo?)
                self._env.configuration.node.create_interface(iface.ip, str(iface.net.netmask), iface.index, iface.id)

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
                s = self._env.configuration.service.create_active_service(service_cfg.type, service_cfg.owner,
                                                                          service_cfg.name, n, service_cfg.access_level,
                                                                          service_cfg.configuration, service_cfg.id)
                self._env.configuration.node.add_service(n, s)
            
            for processor in node.traffic_processors:
                processor_cfg: Union[ActiveServiceConfig, FirewallConfig] = self._refs[processor]
                if isinstance(processor_cfg, ActiveServiceConfig):
                    s = self._env.configuration.service.create_active_service(processor_cfg.type, processor_cfg.owner,
                                                                              processor_cfg.name, n, processor_cfg.access_level,
                                                                              processor_cfg.configuration)
                else:
                    # TODO: Owner/name/access_level not in the config. It should probably be there. Otherwise we have
                    #       to hardcode.
                    s = self._env.configuration.service.create_active_service("firewall", "root",
                                                                              "firewall", n, AccessLevel.ELEVATED,
                                                                              None)

                    # This is not very pretty. But coding around it would require unnecessary expansion of the API.
                    if isinstance(s.active_service, FirewallImpl):
                        impl: FirewallImpl = s.active_service

                        for chain in processor_cfg.chains:
                            impl.set_default_policy(chain.type, chain.policy)
                            for rule in chain.rules:
                                impl.add_rule(chain.type, rule)

                self._env.configuration.node.add_traffic_processor(n, s.active_service)

            self._env.configuration.node.set_shell(n, n.services.get(node.shell, None))

            self._env.configuration.network.add_node(n)

        for router in self._routers:
            r = self._env.configuration.node.create_router(router.id, self._env.messaging)
            # TODO: This one complains that it is the List of Interface configs, while, after config processing it is
            #       a list of strings. This should probably be fixed to keep it type-happy.
            for iface_id in router.interfaces:
                iface = self._obj_refs[iface_id]
                self._env.configuration.node.add_interface(r, iface, iface.index)

            for route in router.routing_table:
                route_obj = self._env.configuration.node.create_route(route.network, route.port, route.metric)
                self._env.configuration.node.add_route(r, route_obj)

            # TODO: Code duplication... this is one of the things to fix once routers and nodes are combined together

            # HACK: To have a sensible default, we add a permissive firewall that enables forwarding on the router if
            # there are no traffic processors specified. The implementation is not pretty.
            have_fw = False
            for processor in router.traffic_processors:
                processor_cfg: Union[ActiveServiceConfig, FirewallConfig] = self._refs[processor]
                if isinstance(processor_cfg, FirewallConfig):
                    have_fw = True

            if not have_fw:
                fw_id = str(uuid.uuid4())
                self._refs[fw_id] = FirewallConfig(
                                        default_policy=FirewallPolicy.DENY,
                                        chains=[
                                            FirewallChainConfig(
                                                type=FirewallChainType.FORWARD,
                                                policy=FirewallPolicy.ALLOW,
                                                rules=[]
                                            )
                                        ]
                                    )
                router.traffic_processors.append(fw_id)

            for processor in router.traffic_processors:
                processor_cfg: Union[ActiveServiceConfig, FirewallConfig] = self._refs[processor]
                if isinstance(processor_cfg, ActiveServiceConfig):
                    s = self._env.configuration.service.create_active_service(processor_cfg.type, processor_cfg.owner,
                                                                              processor_cfg.name, r, processor_cfg.access_level,
                                                                              processor_cfg.configuration)
                else:
                    # TODO: Owner/name/access_level not in the config. It should probably be there. Otherwise we have
                    #       to hardcode.
                    s = self._env.configuration.service.create_active_service("firewall", "root",
                                                                              "firewall", r, AccessLevel.ELEVATED,
                                                                              {"default_policy": processor_cfg.default_policy})

                    # This is not very pretty. But coding around it would require unnecessary expansion of the API.
                    if isinstance(s.active_service, FirewallImpl):
                        impl: FirewallImpl = s.active_service

                        for chain in processor_cfg.chains:
                            impl.set_default_policy(chain.type, chain.policy)
                            for rule in chain.rules:
                                impl.add_rule(chain.type, rule)

                self._env.configuration.node.add_traffic_processor(r, s.active_service)

            self._env.configuration.network.add_node(r)

        # 5) Connections
        for conn_config in self._connections:
            src: NodeImpl = self._obj_refs[conn_config.src_id]
            dst: NodeImpl = self._obj_refs[conn_config.dst_id]

            conn = self._env.configuration.network.add_connection(src, dst, conn_config.src_port, conn_config.dst_port)
            conn = ConnectionImpl.cast_from(conn)

            # Propagate new interfaces back into the configuration
            src_config = self._refs[conn_config.src_id]
            src_port_id = conn.hop.src.port
            src_iface = src.interfaces[src_port_id]

            if conn_config.src_port == -1:
                if isinstance(src_config, RouterConfig):
                    iface_cfg = PortConfig(ip=src_iface.ip, net=src_iface.net, index=src_port_id)
                else:
                    iface_cfg = InterfaceConfig(ip=src_iface.ip, net=src_iface.net, index=src_port_id)

                src_config.interfaces.append(iface_cfg.id)
                self._refs[iface_cfg.id] = iface_cfg
                conn_config.src_port = src_port_id

            # Fix interfaces without explicit index (i.e., taken from a list)
            # At this point, ..._config contains only references to other objects, so the complaint about type mismatch
            # is not valid
            self._refs[src_config.interfaces[src_port_id]].index = src_port_id

            dst_port_id = conn.hop.dst.port
            dst_iface = dst.interfaces[dst_port_id]
            dst_config = self._refs[conn_config.dst_id]

            if conn_config.dst_port == -1:
                if isinstance(dst_config, RouterConfig):
                    iface_cfg = PortConfig(ip=dst_iface.ip, net=dst_iface.net, index=dst_port_id)
                else:
                    iface_cfg = InterfaceConfig(ip=dst_iface.ip, net=dst_iface.net, index=dst_port_id)

                dst_config.interfaces.append(iface_cfg.id)
                self._refs[iface_cfg.id] = iface_cfg
                conn_config.dst_port = dst_port_id

            # Fix interfaces without explicit index (i.e., taken from a list)
            # At this point, ..._config contains only references to other objects, so the complaint about type mismatch
            # is not valid
            self._refs[dst_config.interfaces[dst_port_id]].index = dst_port_id

        return self._env


# ----------------------------------------------------------------------------------------------------------------------
class GeneralConfigurationImpl(GeneralConfiguration):

    def __init__(self, env: Environment) -> None:
        self._env = env
        self._configurator = Configurator()

    def configure(self, *config_item: Union[NetworkConfig, ConnectionConfig, RouterConfig, NodeConfig,
                                            InterfaceConfig, ActiveServiceConfig, PassiveServiceConfig,
                                            AuthorizationConfig, DataConfig]) -> Environment:
        self._configurator.reset()
        self._configurator.configure(self._env, *config_item)
        return self._env

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

        o = self._configurator.get_object_by_id(id)
        if not isinstance(o, object_type):
            raise AttributeError(
                "Attempting to cast object with id: {} to an incompatible type: {}. Type is {}".format(id,
                                                                                                       str(object_type),
                                                                                                       type(o)))
        return o

    def get_objects_by_type(self, type: Type[ObjectType]) -> List[ObjectType]:
        return self._configurator.get_objects_by_type(type)

    def add_object(self, id: str, obj: Any) -> None:
        self._configurator.add_object(id, obj)

    @staticmethod
    def cast_from(o: GeneralConfiguration) -> 'GeneralConfigurationImpl':
        if isinstance(o, GeneralConfigurationImpl):
            return o
        else:
            raise ValueError("Malformed underlying object passed with the GeneralConfiguration interface")


# ----------------------------------------------------------------------------------------------------------------------
# Runtime configuration of the environment. Can be filled from different sources
@dataclass
class RuntimeConfiguration:
    data_backend: str = "MEMORY"
    data_backend_params: Dict[str, str] = field(default_factory=lambda: {})
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config_id: str = ""
    config_filename: str = ""

