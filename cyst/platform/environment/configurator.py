import logging.config
import uuid
import collections

from dataclasses import dataclass, field
from typing import List, Union, Optional, Dict, Any, Type, Tuple, Callable

import jsonpickle

from cyst.api.configuration import AuthenticationTokenConfig
from cyst.api.environment.configuration import GeneralConfiguration, ObjectType, ConfigurationObjectType
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.platform import Platform
from cyst.api.host.service import ActiveService, PassiveService, Service
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.configuration.host.service import ActiveServiceConfig, PassiveServiceConfig
from cyst.api.configuration.infrastructure.infrastructure import InfrastructureConfig
from cyst.api.configuration.infrastructure.log import LogConfig, LogSource, log_defaults
from cyst.api.configuration.logic.access import AuthorizationConfig, AuthenticationProviderConfig, AccessSchemeConfig, \
    AuthorizationDomainConfig, FederatedAuthorizationConfig
from cyst.api.configuration.logic.data import DataConfig
from cyst.api.configuration.logic.exploit import VulnerableServiceConfig, ExploitParameterConfig, ExploitConfig
from cyst.api.configuration.network.elements import PortConfig, InterfaceConfig, ConnectionConfig, RouteConfig, SessionConfig
from cyst.api.configuration.network.firewall import FirewallChainConfig, FirewallConfig, FirewallPolicy, FirewallChainType
from cyst.api.configuration.network.network import NetworkConfig
from cyst.api.configuration.network.router import RouterConfig
from cyst.api.configuration.network.node import NodeConfig
from cyst.api.environment.environment import Environment
from cyst.api.host.service import AccessLevel
from cyst.api.logic.access import AuthenticationTokenSecurity
from cyst.api.network.node import Node

from cyst.platform.network.firewall import FirewallImpl
from cyst.platform.network.elements import ConnectionImpl
from cyst.platform.network.node import NodeImpl
from cyst.platform.host.service import ServiceImpl, PassiveServiceImpl, ServiceState


# ----------------------------------------------------------------------------------------------------------------------
# Converting configuration description to actual objects
# ----------------------------------------------------------------------------------------------------------------------
class Configurator:
    def __init__(self, platform: Platform):
        self._platform = platform
        self._refs: Dict[str, Any] = {}
        self._obj_refs: Dict[str, Any] = {}
        self._connections: List[ConnectionConfig] = []
        self._sessions: List[SessionConfig] = []
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
        self._authentication_tokens: List[AuthenticationTokenConfig] = []
        self._access_schemes: List[AccessSchemeConfig] = []
        self._authorization_domains: List[AuthorizationDomainConfig] = []

    def __getstate__(self):
        result = self.__dict__
        return result

    def __setstate__(self, state):
        self.__dict__.update(state)

    def reset(self):
        self._refs.clear()
        self._obj_refs.clear()
        self._connections.clear()
        self._sessions.clear()
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
        self._authentication_tokens.clear()
        self._access_schemes.clear()
        self._authorization_domains.clear()

    def get_object_by_id(self, id: str, object_type: Type[ObjectType]) -> ObjectType:

        o = self._obj_refs[id]
        error = False

        # We have to do a bit of a black magic to overcome Service type shadowing
        if isinstance(o, ServiceImpl):
            if object_type is ActiveService and o.active_service:
                return o.active_service
            elif object_type is PassiveService and o.passive_service:
                return o.passive_service
            elif object_type is Service:
                return o
            else:
                error = True
        elif not isinstance(o, object_type):
            error = True

        if error:
            raise AttributeError(
                "Attempting to cast object with id: {} to an incompatible type: {}. Type is {}".format(id,
                                                                                                       str(object_type),
                                                                                                       type(o)))

        return o

    def add_object(self, id: str, obj: Any) -> None:
        self._obj_refs[id] = obj

    def process_cfg_item(self, item: ConfigItem):
        mapping = {
            ConnectionConfig: self._connections,
            SessionConfig: self._sessions,
            RouterConfig: self._routers,
            NodeConfig: self._nodes,
            InterfaceConfig: self._interfaces,
            ActiveServiceConfig: self._active_services,
            PassiveServiceConfig: self._passive_services,
            AuthorizationConfig: self._authorizations,
            DataConfig: self._data,
            FirewallConfig: self._firewalls,
            ExploitConfig: self._exploits,
            AuthenticationProviderConfig: self._authentication_providers,
            AccessSchemeConfig: self._access_schemes,
            AuthorizationDomainConfig: self._authorization_domains,
            FederatedAuthorizationConfig: self._authorizations,
            AuthenticationTokenConfig: self._authentication_tokens
        }

        for key, value in item.__dict__.items():
            if not isinstance(value, list):
                value = [value]
            for v in value:
                if type(v) in mapping:
                    self.process_cfg_item(v)

        if type(item) in mapping:
            mapping[type(item)].append(item)  # For once, the type inspection is helpless here

        self._refs[item.ref] = item

    # ------------------------------------------------------------------------------------------------------------------
    # Gather all configuration items
    def configure(self,
                  *configs: Union[NetworkConfig, ConnectionConfig, RouterConfig, NodeConfig,
                                  InterfaceConfig, ActiveServiceConfig, PassiveServiceConfig,
                                  AuthorizationConfig, DataConfig]) -> None:

        # --------------------------------------------------------------------------------------------------------------
        # Store all the configuration items
        # Each type to its own. I am basically exploding the configuration again. It would be better to go top-down,
        # considering it is already pre-configured, but this has to be done in another merge request.
        for config in configs:
            self.process_cfg_item(config)

        # --------------------------------------------------------------------------------------------------------------
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
            scheme_instance = self._platform.configuration.access.create_access_scheme(scheme.id)

            # Authorization domain is passed on as a full class from pre-configuration, not as an ID
            # authorization_domain = self._refs[scheme.authorization_domain]
            authorization_domain = scheme.authorization_domain

            # Go through all providers and if they do not exist instantiate them
            for provider_conf in scheme.authentication_providers:
                if isinstance(provider_conf, str):
                    provider_conf: AuthenticationProviderConfig = self._refs[provider_conf]

                if provider_conf.id not in self._obj_refs:
                    provider = self._platform.configuration.access.create_authentication_provider(
                        provider_conf.provider_type,
                        provider_conf.token_type,
                        provider_conf.token_security,
                        provider_conf.ip,
                        provider_conf.timeout,
                        provider_conf.id
                    )
                else:
                    provider = self._obj_refs[provider_conf.id]

                self._platform.configuration.access.add_provider_to_scheme(provider, scheme_instance)

            for auth in authorization_domain.authorizations:
                auth = self._refs[auth.ref]
                if isinstance(auth, AuthorizationConfig) or isinstance(auth, FederatedAuthorizationConfig):
                    identity = auth.identity

                    # This is not very pretty, but the original version that ran this code for each provider caused
                    # problems with the new approach that correctly tracks IDs of objects. In this case objects with
                    # identical IDs could be created multiple times.
                    for provider_conf in scheme.authentication_providers:
                        self._platform.configuration.access.create_and_register_authentication_token(self._obj_refs[provider_conf.id], identity)

                    # WARN: this creates authorizations with services = ["*"], nodes = ["*"] if not Federated is
                    # created, when the authorization process is
                    # done, these are only used as templates so should not be a problem
                    authorization = self._platform.configuration.access.create_authorization(auth.identity,
                                                                                        auth.access_level, auth.id)\
                        if not isinstance(auth, FederatedAuthorizationConfig) else \
                        self._platform.configuration.access.create_authorization(auth.identity, auth.access_level,
                                                                            auth.id, auth.nodes, auth.services)

                    self._platform.configuration.access.add_authorization_to_scheme(authorization, scheme_instance)
                else:
                    raise RuntimeError("Wrong object type provided instead of (Federated)AuthorizationConfig")

        # Also add separately defined authentication tokens
        # Currently, we only consider local tokens
        for token_cfg in self._authentication_tokens:
            token = None
            for provider_ref in token_cfg.providers:
                provider_conf: AuthenticationProviderConfig = self._refs[provider_ref]

                if not token:
                    token = self._platform.configuration.access.create_authentication_token(type=provider_conf.token_type,
                                                                                            security=AuthenticationTokenSecurity.OPEN,
                                                                                            identity=token_cfg.identity,
                                                                                            is_local=True)
                    self._obj_refs[token_cfg.id] = token
                else:
                    if provider_conf.token_type != token.type:
                        raise RuntimeError(f"Attempting to bind a token of type {token.type} to a authentication provider of type {provider_conf.token_type}.")

                self._platform.configuration.access.register_authentication_token(self._obj_refs[provider_conf.id], token)

        for data in self._data:
            d = self._platform.configuration.service.create_data(data.id, data.owner, data.path, data.description)

        for exploit in self._exploits:
            params = []
            if exploit.parameters:
                for p in exploit.parameters:
                    param = self._platform.configuration.exploit.create_exploit_parameter(p.type, p.value, p.immutable)
                    params.append(param)

            services = []
            for s in exploit.services:
                service = self._platform.configuration.exploit.create_vulnerable_service(s.service, s.min_version,
                                                                                    s.max_version)
                services.append(service)

            e = self._platform.configuration.exploit.create_exploit(exploit.id, services, exploit.locality, exploit.category,
                                                               *params)

            self._platform.configuration.exploit.add_exploit(e)

        # 2) Passive Services
        passive_service_obj = {}
        for service in self._passive_services:
            s = self._platform.configuration.service.create_passive_service(service.name, service.owner, service.version,
                                                                       service.local, service.access_level, service.id)
            # This was pre-split managed in _run method of the environment, but as PassiveServiceImpl is now
            # platform-specific, there is no clear way to set it there.
            PassiveServiceImpl.cast_from(s.passive_service).set_state(ServiceState.RUNNING)

            for d in service.public_data:
                self._platform.configuration.service.public_data(s.passive_service).append(self._obj_refs[d.id])
            for d in service.private_data:
                self._platform.configuration.service.private_data(s.passive_service).append(self._obj_refs[d.id])
            for a in service.public_authorizations:
                self._platform.configuration.service.public_authorizations(s.passive_service).append(self._obj_refs[a.id])
            for a in service.private_authorizations:
                self._platform.configuration.service.private_authorizations(s.passive_service).append(self._obj_refs[a.id])

            for p in service.parameters:
                self._platform.configuration.service.set_service_parameter(s.passive_service, p[0], p[1])

            for prov in service.authentication_providers:
                self._platform.configuration.service.provides_auth(s,
                                                              self._obj_refs[prov.id if isinstance(prov,
                                                                            AuthenticationProviderConfig) else prov])

            for scheme in service.access_schemes:
                self._platform.configuration.service.set_scheme(s.passive_service, self._obj_refs[
                    scheme.id if isinstance(scheme, AccessSchemeConfig) else scheme])

            passive_service_obj[service.id] = s

        # 3) Interfaces
        for iface in self._interfaces:
            if isinstance(iface, PortConfig):
                self._platform.configuration.node.create_port(iface.ip, str(iface.net.netmask), iface.index, iface.id)
            else:
                # TODO: Missing a setting of a gateway (Really todo?)
                self._platform.configuration.node.create_interface(iface.ip, str(iface.net.netmask), iface.index, iface.id)

        # 4) Nodes
        for node in self._nodes:
            n = self._platform.configuration.node.create_node(node.id)
            for i in node.interfaces:
                obj_i = self._obj_refs[i.id]
                self._platform.configuration.node.add_interface(n, obj_i, obj_i.index)

            for service in node.passive_services:
                self._platform.configuration.node.add_service(n, passive_service_obj[service.id])

            for service_cfg in node.active_services:
                s = self._platform.configuration.service.create_active_service(service_cfg.type, service_cfg.owner,
                                                                               service_cfg.name, n, service_cfg.access_level,
                                                                               service_cfg.configuration,
                                                                               service_cfg.id)
                self._platform.configuration.node.add_service(n, s)
            
            for processor_cfg in node.traffic_processors:
                if isinstance(processor_cfg, ActiveServiceConfig):
                    s = self._platform.configuration.service.create_active_service(processor_cfg.type, processor_cfg.owner,
                                                                                   processor_cfg.name, n, processor_cfg.access_level,
                                                                                   processor_cfg.configuration,
                                                                                   processor_cfg.id)
                else:
                    # TODO: Owner/name/access_level not in the config. It should probably be there. Otherwise we have
                    #       to hardcode.
                    s = self._platform.configuration.service.create_active_service("firewall", "root",
                                                                                   "firewall", n, AccessLevel.ELEVATED,
                                                                                   None,
                                                                                   node.id + ".firewall_0")  # TODO: This is definitely wrong in the new naming scheme

                    # This is not very pretty. But coding around it would require unnecessary expansion of the API.
                    if isinstance(s, FirewallImpl):
                        impl: FirewallImpl = s

                        for chain in processor_cfg.chains:
                            impl.set_default_policy(chain.type, chain.policy)
                            for rule in chain.rules:
                                impl.add_rule(chain.type, rule)

                self._platform.configuration.node.add_traffic_processor(n, s)

            self._platform.configuration.node.set_shell(n, n.services.get(node.shell, None))

            self._platform.configuration.network.add_node(n)

        # TODO, HACK: Any source of messages has to be an active service, so that it is registered in the system
        #             and passed the correct EnvironmentMessaging, i.e., we can't just pass the platform one.
        #             Therefore, in this case we just create a dummy active service and access the underlying
        #             environment's messaging. It is unholy, but it will change when the router is turned into
        #             a correct active service. I don't be rewriting the documentation and network API though,
        #             that will be a major pain in the ass.
        dummy_service = self._platform.configuration.service.create_active_service("scripted_actor", "__dummy", "__dummy",
                                                                                   NodeImpl(str(uuid.uuid4())),
                                                                                   AccessLevel.LIMITED,
                                                                                   None, str(uuid.uuid4()))
        platform_messaging: EnvironmentMessaging = dummy_service.active_service._messaging

        for router in self._routers:
            r = self._platform.configuration.node.create_router(router.id, platform_messaging)
            # TODO: This one complains that it is the List of Interface configs, while, after config processing it is
            #       a list of strings. This should probably be fixed to keep it type-happy.
            for iface_cfg in router.interfaces:
                iface = self._obj_refs[iface_cfg.id]
                self._platform.configuration.node.add_interface(r, iface, iface.index)

            for route in router.routing_table:
                route_obj = self._platform.configuration.node.create_route(route.network, route.port, route.metric)
                self._platform.configuration.node.add_route(r, route_obj)

            # TODO: Code duplication... this is one of the things to fix once routers and nodes are combined together

            # HACK: To have a sensible default, we add a permissive firewall that enables forwarding on the router if
            # there are no traffic processors specified. The implementation is not pretty.
            have_fw = False
            for processor_cfg in router.traffic_processors:
                if isinstance(processor_cfg, FirewallConfig):
                    have_fw = True

            if not have_fw:
                fw_id = str(uuid.uuid4())
                cfg = FirewallConfig(
                                        default_policy=FirewallPolicy.DENY,
                                        chains=[
                                            FirewallChainConfig(
                                                type=FirewallChainType.FORWARD,
                                                policy=FirewallPolicy.ALLOW,
                                                rules=[]
                                            )
                                        ]
                                    )
                self._refs[fw_id] = cfg
                router.traffic_processors.append(cfg)

            for processor_cfg in router.traffic_processors:
                if isinstance(processor_cfg, ActiveServiceConfig):
                    s = self._platform.configuration.service.create_active_service(processor_cfg.type, processor_cfg.owner,
                                                                              processor_cfg.name, r, processor_cfg.access_level,
                                                                              processor_cfg.configuration)  # TODO: Default ID unknown
                else:
                    # TODO: Owner/name/access_level not in the config. It should probably be there. Otherwise we have
                    #       to hardcode.
                    s = self._platform.configuration.service.create_active_service("firewall", "root",
                                                                              "firewall", r, AccessLevel.ELEVATED,
                                                                              {"default_policy": processor_cfg.default_policy}) # TODO: Default ID not known

                    # This is not very pretty. But coding around it would require unnecessary expansion of the API.
                    if isinstance(s.active_service, FirewallImpl):
                        impl: FirewallImpl = s.active_service

                        for chain in processor_cfg.chains:
                            impl.set_default_policy(chain.type, chain.policy)
                            for rule in chain.rules:
                                impl.add_rule(chain.type, rule)

                self._platform.configuration.node.add_traffic_processor(r, s.active_service)

            self._platform.configuration.network.add_node(r)

        # 5) Connections
        for conn_config in self._connections:
            src: NodeImpl = self._obj_refs[self._refs[conn_config.src_ref].id]
            dst: NodeImpl = self._obj_refs[self._refs[conn_config.dst_ref].id]

            conn = self._platform.configuration.network.add_connection(src, dst, conn_config.src_port, conn_config.dst_port)
            conn = ConnectionImpl.cast_from(conn)

            # Propagate new interfaces back into the configuration
            src_config = self._refs[conn_config.src_ref]
            src_port_id = conn.hop.src.port
            src_iface = src.interfaces[src_port_id]

            if conn_config.src_port == -1:
                if isinstance(src_config, RouterConfig):
                    iface_cfg = PortConfig(ip=src_iface.ip, net=src_iface.net, index=src_port_id)
                else:
                    iface_cfg = InterfaceConfig(ip=src_iface.ip, net=src_iface.net, index=src_port_id)

                src_config.interfaces.append(iface_cfg)
                self._refs[iface_cfg.ref] = iface_cfg
                conn_config.src_port = src_port_id

            # Fix interfaces without explicit index (i.e., taken from a list)
            # At this point, ..._config contains only references to other objects, so the complaint about type mismatch
            # is not valid
            self._refs[src_config.interfaces[src_port_id].ref].index = src_port_id

            dst_port_id = conn.hop.dst.port
            dst_iface = dst.interfaces[dst_port_id]
            dst_config = self._refs[conn_config.dst_ref]

            if conn_config.dst_port == -1:
                if isinstance(dst_config, RouterConfig):
                    iface_cfg = PortConfig(ip=dst_iface.ip, net=dst_iface.net, index=dst_port_id)
                else:
                    iface_cfg = InterfaceConfig(ip=dst_iface.ip, net=dst_iface.net, index=dst_port_id)

                dst_config.interfaces.append(iface_cfg.ref)
                self._refs[iface_cfg.ref] = iface_cfg
                conn_config.dst_port = dst_port_id

            # Fix interfaces without explicit index (i.e., taken from a list)
            # At this point, ..._config contains only references to other objects, so the complaint about type mismatch
            # is not valid
            # TODO: I am fixing it to just shut it up. I am not currently sure, what is the reason why only id and not
            #       the config is present here.
            if isinstance(dst_config.interfaces[dst_port_id], str):
                self._refs[dst_config.interfaces[dst_port_id]].index = dst_port_id
            else:
                self._refs[dst_config.interfaces[dst_port_id].ref].index = dst_port_id

        # Sessions
        for session_cfg in self._sessions:
            # Check if the waypoints and services are given in terms of IDs or in terms of configuration refs. If the
            # latter, resolve it to IDs.
            waypoints = []
            for waypoint in session_cfg.waypoints:
                if isinstance(waypoint, str) and waypoint in self._refs:
                    waypoints.append(self._refs[waypoint].id)
                elif isinstance(waypoint, NodeConfig) or isinstance(waypoint, RouterConfig):
                    waypoints.append(waypoint.id)
                else:
                    waypoints.append(waypoint)

            services = []
            for service in [session_cfg.src_service, session_cfg.dst_service]:
                if isinstance(service, str) and service in self._refs:
                    services.append(self._refs[service].id.split(".")[-1])
                elif isinstance(service, PassiveServiceConfig):
                    services.append(service.id.split(".")[-1])
                else:
                    services.append(service)

            self._platform.configuration.network.create_session(owner="__system",
                                                                waypoints=waypoints,
                                                                src_service=services[0],
                                                                dst_service=services[1],
                                                                parent=None,
                                                                defer=True,
                                                                reverse=session_cfg.reverse,
                                                                id=session_cfg.id)
