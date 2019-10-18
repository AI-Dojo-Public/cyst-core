import ipaddress
import networkx as nx

from typing import Tuple, NamedTuple, Optional, List

from environment.message import Message, MessageType, Response, Status, StatusOrigin, StatusValue
from environment.node import Node


# This is not a very optimized approach, but as long it does not slow down the execution... meh
class Route(NamedTuple):
    net: ipaddress.IPv4Network
    id: str


class Switch(Node):

    # As much I hate to have env untyped, forcing a type check on this results in a cyclic dependency hell
    def __init__(self, id: str, ip: str, mask: str, env) -> None:
        if not ip:
            raise Exception("A switch cannot be instantiated without an IP specified")

        if not mask:
            raise Exception("A switch cannot be instantiated without a mask specified")

        super(Switch, self).__init__(id, "Switch", ip, mask)

        self._env = env

        self._ports = []
        self._node_ids = {}
        self._switch_ids = set()
        self._routes = []

    def connect_node(self, node: Node) -> Tuple[bool, str]:
        # Do not process already processed nodes
        if node.id in self._node_ids:
            return False, "Node already connected"

        assigned_ip = node.ip
        # If the node does not have an address, assign one from the pool
        if not assigned_ip:
            for h in self._net.hosts():
                # The fact that I am casting it back and forth from string to ip is abhorrent. But unless this proves
                # to be a real performance issue, I am leaving it as-is
                addr = str(h)
                if addr != self.ip and addr not in self._ports:
                    assigned_ip = addr
                    break

            if not assigned_ip:
                return False, "Do not have any more addresses to allocate"

        else:
            if node.gateway != self.ip:
                return False, "Connecting node to wrong gateway"

        self._node_ids[node.id] = len(self._ports)
        self._ports.append(assigned_ip)

        # Set node parameters
        node.set_ip(assigned_ip)
        node.set_mask(str(self._net.netmask))

        # Propagate the information to the network
        self._env.network.update_node_ip(node, assigned_ip)

    def connect_switch(self, switch: 'Switch') -> Tuple[bool, str]:
        if self._net.overlaps(switch._net):
            return False, "Switches {} and {} overlaps in their network.".format(self.id, switch.id)

        if switch.id in self._switch_ids:
            return False, "Switch {} already connected with {}".format(self.id, switch.id)

        # Update routing tables on both sides
        self._routes.append(Route(switch._net, switch.id))
        self._switch_ids.add(switch.id)

        switch._routes.append(Route(self._net, self.id))
        switch._switch_ids.add(self.id)

    def process_message(self, message: Message) -> Tuple[bool, int]:
        if message.type == MessageType.ACK:
            return True, 0

        target_ip = ipaddress.ip_address(message.target)

        # The target is in this switch's constituency
        if target_ip in self._net:
            # And the target even exists
            if message.target in self._ports:
                message.set_next_hop(message.target)
                return True, 1
            # The target is not there
            else:
                m = Response(message.id, source=message.target, target=message.source, status=Status(StatusOrigin.NETWORK, StatusValue.FAILURE), content="Host unreachable")
                m.set_next_hop(self.ip)
                self._env.send_message(m)
                return False, 1

        else:
            for route in self._routes:
                if target_ip in route.net:
                    message.set_next_hop(route.id)
                    return True, 1

            m = Response(message.id, source=message.target, target=message.source, status=Status(StatusOrigin.NETWORK, StatusValue.FAILURE), content="Network address {} not routable".format(message.target))
            m.set_next_hop(self.ip)
            self._env.send_message(m)
            return False, 1


# This class is here as a future proofing
class Connection:
    def __init__(self):
        pass


class Network:
    def __init__(self):
        self._nodes_by_id = {}
        self._nodes_by_ip = {}
        self._graph = nx.Graph()
        self._switches = {}

    def add_node(self, node: Node) -> None:
        # Ignore already present nodes
        if node.id in self._nodes_by_id:
            return

        self._nodes_by_id[node.id] = node

        if node.ip:
            self._nodes_by_ip[node.ip] = node
            if isinstance(node, Switch):
                self._switches[node.ip] = node.id

        self._graph.add_node(node.id, node=node)

    def update_node_ip(self, node: Node, ip: str):
        self._nodes_by_ip[ip] = node

    def add_connection(self, n1: Node, n2: Node, connection: Connection = None) -> None:
        if not n1 or not n2:
            raise Exception("Could not add connection between nonexistent nodes")

        if not connection:
            connection = Connection()

        if isinstance(n1, Switch):
            if isinstance(n2, Switch):
                n1.connect_switch(n2)
            else:
                n1.connect_node(n2)
        elif isinstance(n2, Switch):
            n2.connect_node(n1)

        self._graph.add_edge(n1.id, n2.id, connection=connection)

    def get_node_by_ip(self, ip: str = "") -> Optional[str]:
        if not ip:
            return None
        else:
            return self._nodes_by_ip.get(ip, None)

    def get_node_by_id(self, id: str = "") -> Optional[str]:
        if not id:
            return None
        else:
            return self._nodes_by_id.get(id, None)

    def get_nodes_by_type(self, type: str = "") -> List[Node]:
        if not type:
            return list(self._nodes_by_id.values())
        else:
            return [x for x in self._nodes_by_id.values() if x.type == type]

    def reset(self) -> None:
        self._nodes_by_id.clear()
        self._graph.clear()
        self._switches.clear()
