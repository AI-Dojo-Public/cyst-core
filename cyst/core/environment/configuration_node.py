from __future__ import annotations

import uuid

from typing import TYPE_CHECKING, List, Union

from netaddr import IPAddress, IPNetwork

from cyst.api.environment.configuration import NodeConfiguration
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.host.service import ActiveService, Service
from cyst.api.network.elements import Route, Interface
from cyst.api.network.firewall import FirewallPolicy, FirewallRule
from cyst.api.network.node import Node

from cyst.core.host.service import ServiceImpl
from cyst.core.network.elements import InterfaceImpl
from cyst.core.network.node import NodeImpl
from cyst.core.network.router import Router

if TYPE_CHECKING:
    from cyst.core.environment.environment import _Environment


class NodeConfigurationImpl(NodeConfiguration):
    def __init__(self, env: _Environment):
        self._env = env

    def create_node(self, id: str, ip: Union[str, IPAddress] = "", mask: str = "", shell: Service = None) -> Node:
        return _create_node(self._env, id, ip, mask, shell)

    def create_router(self, id: str, messaging: EnvironmentMessaging) -> Node:
        return _create_router(self._env, id, messaging)

    def create_interface(self, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0,
                         id: str = "") -> Interface:
        return _create_interface(self._env, ip, mask, index, id)

    def create_route(self, net: IPNetwork, port: int, metric: int, id: str = "") -> Route:
        return _create_route(self._env, net, port, metric, id)

    def add_interface(self, node: Node, interface: Interface, index: int = -1) -> int:
        if node.type == "Router":
            return Router.cast_from(node).add_port(interface.ip, interface.mask, index)
        else:
            return NodeImpl.cast_from(node).add_interface(InterfaceImpl.cast_from(interface))

    def set_interface(self, interface: Interface, ip: Union[str, IPAddress] = "", mask: str = "") -> None:
        iface = InterfaceImpl.cast_from(interface)

        if ip:
            iface.set_ip(ip)

        if mask:
            iface.set_mask(mask)

    def add_service(self, node: Node, *service: Service) -> None:
        node = NodeImpl.cast_from(node)

        for srv in service:
            node.add_service(ServiceImpl.cast_from(srv))

    def remove_service(self, node: Node, *service: Service) -> None:
        node = NodeImpl.cast_from(node)

        for srv in service:
            node.remove_service(ServiceImpl.cast_from(srv))

    def set_shell(self, node: Node, service: Service) -> None:
        NodeImpl.cast_from(node).set_shell(service)

    def add_traffic_processor(self, node: Node, processor: ActiveService) -> None:
        node = NodeImpl.cast_from(node)

        node.add_traffic_processor(processor)

    def add_route(self, node: Node, *route: Route) -> None:
        if node.type != "Router":
            raise RuntimeError("Attempting to add route to non-router node")

        for r in route:
            Router.cast_from(node).add_route(r)

    def add_routing_rule(self, node: Node, rule: FirewallRule) -> None:
        if node.type != "Router":
            raise RuntimeError("Attempting to add route to non-router node")

        Router.cast_from(node).add_routing_rule(rule)

    def set_routing_policy(self, node: Node, policy: FirewallPolicy) -> None:
        if node.type != "Router":
            raise RuntimeError("Attempting to set routing policy to non-router node")

        Router.cast_from(node).set_default_routing_policy(policy)

    def list_routes(self, node: Node) -> List[Route]:
        if node.type != "Router":
            raise RuntimeError("Attempting to add route to non-router node")

        return Router.cast_from(node).list_routes()


# ------------------------------------------------------------------------------------------------------------------
# NodeConfiguration
def _create_node(self: _Environment, id: str, ip: Union[str, IPAddress] = "", mask: str = "", shell: Service = None) -> Node:
    n = NodeImpl(id, "Node", ip, mask, shell)
    self._general_configuration.add_object(id, n)
    return n


def _create_router(self: _Environment, id: str, messaging: EnvironmentMessaging) -> Node:
    r = Router(id, messaging)
    self._general_configuration.add_object(id, r)
    return r


def _create_interface(self: _Environment, ip: Union[str, IPAddress] = "", mask: str = "", index: int = 0, id: str = "") -> Interface:
    if not id:
        id = str(uuid.uuid4())
    i = InterfaceImpl(ip, mask, index, id)
    self._general_configuration.add_object(id, i)
    return i


def _create_route(self: _Environment, net: IPNetwork, port: int, metric: int, id: str = "") -> Route:
    if not id:
        id = str(uuid.uuid4())
    r = Route(net, port, metric, id)
    self._general_configuration.add_object(id, r)
    return r
