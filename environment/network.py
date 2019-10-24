import ipaddress
import networkx as nx
import uuid

from collections import Iterable
from typing import Tuple, NamedTuple, Optional, List

from environment.message import Message, MessageType, Response, Status, StatusOrigin, StatusValue
from environment.node import Node


# This is not a very optimized approach, but as long it does not slow down the execution... meh
class Route(NamedTuple):
    net: ipaddress.IPv4Network
    ip: str


class Switch(Node):

    # As much I hate to have env untyped, forcing a type check on this results in a cyclic dependency hell
    def __init__(self, id: str, ip: str, mask: str, env) -> None:
        if not ip:
            raise Exception("A switch cannot be instantiated without an IP specified")

        if not mask:
            raise Exception("A switch cannot be instantiated without a mask specified")

        super(Switch, self).__init__(id, "Switch", ip, mask)

        self._env = env

        self._node_ips = set()
        self._switch_ips = set()
        self._routes = []

    def connect_node(self, node: Node) -> Tuple[bool, str]:
        # Do not process already processed nodes
        if node.ip in self._node_ips:
            return False, "Node already connected"

        assigned_ip = node.ip
        # If the node does not have an address, assign one from the pool
        if not assigned_ip:
            for h in self._net.hosts():
                # The fact that I am casting it back and forth from string to ip is abhorrent. But unless this proves
                # to be a real performance issue, I am leaving it as-is
                addr = str(h)
                if addr != self.ip and addr not in self._node_ips:
                    assigned_ip = addr
                    break

            if not assigned_ip:
                return False, "Do not have any more addresses to allocate"

        else:
            if node.gateway != self.ip:
                return False, "Connecting node to wrong gateway"

        self._node_ips.add(assigned_ip)

        # If the node was originally without an IP, assign it
        if not node.ip:
            # Set node parameters
            node.set_ip(assigned_ip)
            node.set_mask(str(self._net.netmask))

            # Propagate the information to the network
            self._env.network.update_node_ip(node, assigned_ip)

    def connect_switch(self, switch: 'Switch') -> Tuple[bool, str]:
        if self._net.overlaps(switch._net):
            return False, "Switches {} and {} overlaps in their network.".format(self.id, switch.id)

        if switch.ip in self._switch_ips:
            return False, "Switch {} already connected with {}".format(self.id, switch.id)

        # Update routing tables on both sides
        self._routes.append(Route(switch._net, switch.ip))
        self._switch_ips.add(switch.ip)

        switch._routes.append(Route(self._net, self.ip))
        switch._switch_ips.add(self.ip)

    def process_message(self, message: Message) -> Tuple[bool, int]:
        if message.type == MessageType.ACK:
            return True, 0

        # If message is still going through a session then pass it along where it should go
        if message.in_session:
            message.set_next_hop()
            return True, 1

        target_ip = ipaddress.ip_address(message.target)
        if message.type == MessageType.RESPONSE and message.session:
            target_ip = ipaddress.ip_address(message.session.endpoint)

        # The target is in this switch's constituency
        if target_ip in self._net:
            # And the target even exists
            if str(target_ip) in self._node_ips:
                message.set_next_hop(str(target_ip))
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
                    message.set_next_hop(route.ip)
                    return True, 1

            m = Response(message.id, source=message.target, target=message.source, status=Status(StatusOrigin.NETWORK, StatusValue.FAILURE), content="Network address {} not routable".format(message.target))
            m.set_next_hop(self.ip)
            self._env.send_message(m)
            return False, 1


# This class is here as a future proofing
class Connection:
    def __init__(self):
        pass


# The session represents an existing chain of connections, which can be traversed without authorization by its owner
class Session:
    def __init__(self, owner: str, parent: 'Session' = None, path: List[str] = None) -> None:
        self._id = uuid.uuid4()
        if not owner:
            raise Exception("Cannot create a session without an owner")

        self._owner = owner
        self._parent = parent

        if self._parent and parent.owner != self._owner:
            raise Exception("Cannot link sessions with different owners")

        if not path:
            raise Exception("Cannot create a session without a path")

        self._path = path
        self._endpoint = path[-1]

        if self._parent and self._parent.endpoint == self._endpoint:
            raise Exception("Cannot create a session sharing an endpoint with a parent")

    class ForwardIterator(Iterable):
        def __init__(self, session: 'Session') -> None:
            self._session = session
            self._path_index = 0
            if session.parent:
                self._parent_iterator = session.parent.get_forward_iterator()
            else:
                self._parent_iterator = None
            self._parent_traversed = False
            # The last element is to ensure de-duplication of nodes between sessions, because they share ends and begins
            self._last = ""

        def has_next(self) -> bool:
            if self._parent_iterator and self._parent_iterator.has_next():
                return True

            # has_next ignores that __next__ can jump two items during iteration, because it would be a problem only if
            # a second session had only one element (creating session on itself)
            if self._path_index != len(self._session.path):
                return True

            return False

        def __iter__(self):
            return self

        def __next__(self) -> str:
            if self._parent_traversed or not self._session.parent:
                if self._path_index != len(self._session.path):
                    result = self._session.path[self._path_index]
                    self._path_index += 1

                    # Skip duplicate nodes on the session endpoints
                    if result == self._last:
                        return self.__next__()
                    else:
                        self._last = result
                        return result
                else:
                    raise StopIteration
            else:
                if self._parent_iterator.has_next():
                    result = self._parent_iterator.__next__()
                    self._last = result
                    return result
                else:
                    self._parent_traversed = True
                    return self.__next__()

    class ReverseIterator(Iterable):
        def __init__(self, session: 'Session') -> None:
            self._session = session
            self._path_index = len(self._session.path) - 1
            if session.parent:
                self._parent_iterator = session.parent.get_reverse_iterator()
            else:
                self._parent_iterator = None
            self._parent_traversing = False
            # The last element is to ensure de-duplication of nodes between sessions, because they share ends and begins
            self._last = ""

        def has_next(self) -> bool:
            if self._path_index >= 0:
                return True

            elif self._parent_iterator:
                return self._parent_iterator.has_next()

            return False

        def __iter__(self):
            return self

        def __next__(self) -> str:
            if self._path_index >= 0:
                result = self._session.path[self._path_index]
                self._path_index -= 1
                self._last = result
                return result
            else:
                if not self._parent_traversing:
                    self._parent_traversing = True
                    return self.__next__()
                else:
                    if self._parent_iterator.has_next():
                        result = self._parent_iterator.__next__()
                        # Skip duplicate nodes on the session endpoints
                        if result == self._last:
                            result = self._parent_iterator.__next__()

                        self._last = result
                        return result
                    else:
                        raise StopIteration

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def id(self) -> str:
        return str(self._id)

    @property
    def parent(self) -> 'Session':
        return self._parent

    @property
    def path(self) -> List[str]:
        return self._path

    def get_forward_iterator(self) -> ForwardIterator:
        return Session.ForwardIterator(self)

    def get_reverse_iterator(self) -> ReverseIterator:
        return Session.ReverseIterator(self)

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def __str__(self) -> str:
        result = []
        for node in self.get_forward_iterator():
            result.append(node)
        return "[ID: {}, Owner: {}, Path: {}]".format(self.id, self.owner, result)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other) -> bool:
        if not other:
            return False

        return self.owner == other.owner and \
            self.parent == other.parent and \
            self.path == other.path


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
