import unittest

from netaddr import IPAddress, IPNetwork

from attackers.simple import SimpleAttacker
from environment.access import Authorization, AccessLevel, Policy
from environment.action import ActionList
from environment.environment import Environment, EnvironmentProxy
from environment.message import StatusOrigin, StatusValue
from environment.network import Router
from environment.network_elements import Session, Interface, Endpoint, Hop, Route
from environment.node import Node, PassiveService, ActiveService


class TestInterface(unittest.TestCase):

    def test_0000(self):
        i1 = Interface()

        self.assertEqual(i1.ip, None, "Empty IP constructor")
        self.assertEqual(i1.mask, None, "Empty mask constructor")

        # Setting mask without IP
        with self.assertRaises(Exception):
            i1.set_mask("255.255.255.0")

        i2 = Interface(ip="127.0.0.1")

        self.assertEqual(str(i2.ip), "127.0.0.1", "Correct IP address")

        #  "Wrong IP address"
        with self.assertRaises(Exception):
            i3 = Interface(ip="276.0.0.1")

        # Mask without IP
        with self.assertRaises(Exception):
            i4 = Interface(mask="255.255.255.0")

        i5 = Interface(ip="10.0.0.2", mask="255.0.0.0")

        self.assertEqual(i5.mask, "255.0.0.0", "Correct mask counted")
        self.assertEqual(i5.gateway_ip, IPAddress("10.0.0.1"), "Correct gateway derived")

        i5.set_ip("10.0.1.9")

        self.assertEqual(i5.mask, "255.0.0.0", "Mask unchanged")
        self.assertEqual(i5.gateway_ip, IPAddress("10.0.0.1"), "Gateway unchanged")

        i5.set_mask("255.255.255.0")

        self.assertEqual(i5.gateway_ip, IPAddress("10.0.1.1"), "Gateway recomputed")


class TestSessions(unittest.TestCase):

    def test_0000_single_session(self):
        with self.assertRaises(Exception):
            s0 = Session(owner="", path=[Hop(Endpoint("node1", 0), Endpoint("node2", 0)), Hop(Endpoint("node2", 1), Endpoint("node3", 0))])

        s1 = Session("user1", path=[Hop(Endpoint("node1", 0), Endpoint("node2", 0)), Hop(Endpoint("node2", 1), Endpoint("node3", 0))])
        it = s1.get_forward_iterator()

        self.assertTrue(it.has_next(), "Forward iterator has some elements")
        hop = next(it)
        self.assertEqual(hop.src.id, "node1", "Correct first iteration - source")
        self.assertEqual(hop.dst.id, "node2", "Correct first iteration - destination")
        hop = next(it)
        self.assertEqual(hop.src.id, "node2", "Correct second iteration")
        self.assertEqual(hop.dst.id, "node3", "Correct third iteration")
        self.assertFalse(it.has_next(), "Forward iterator has no elements left")
        with self.assertRaises(StopIteration):
            next(it)

    def test_0001_multiple_sessions(self):
        s1 = Session("user1", path=[Hop(Endpoint("node1", 0), Endpoint("node2", 0)), Hop(Endpoint("node2", 1), Endpoint("node3", 0))])
        s2 = Session("user1", parent=s1, path=[Hop(Endpoint("node3", 1), Endpoint("node4", 0)), Hop(Endpoint("node4", 1), Endpoint("node5", 0))])
        s3 = Session("user1", parent=s2, path=[Hop(Endpoint("node5", 1), Endpoint("node6", 0))])

        it = s3.get_forward_iterator()
        self.assertTrue(it.has_next(), "Forward iterator has some elements")
        hop = next(it)
        self.assertEqual(hop.src.id, "node1", "Correct first iteration - source")
        self.assertEqual(hop.dst.id, "node2", "Correct first iteration - destination")
        next(it)
        hop = next(it)
        self.assertEqual(hop.src.id, "node3", "Correct parent jump - source")
        self.assertEqual(hop.dst.id, "node4", "Correct parent jump - destination")
        next(it)
        hop = next(it)
        self.assertEqual(hop.src.id, "node5", "Correct parent jump and path addition - source")
        self.assertEqual(hop.dst.id, "node6", "Correct parent jump and path addition - destination")
        self.assertFalse(it.has_next(), "Forward iterator has no elements left")
        with self.assertRaises(StopIteration):
            next(it)

        with self.assertRaises(Exception):
            s4 = Session("user2", parent=s3, path=[Hop(Endpoint("node6", 1), Endpoint("node7", 0))])

        with self.assertRaises(Exception):
            s5 = Session("user1", parent=s1, path=[Hop(Endpoint("node2", 1), Endpoint("node3", 0))])

        it2 = s3.get_reverse_iterator()
        self.assertTrue(it2.has_next(), "Reverse iterator has some elements")
        hop = next(it2)
        self.assertEqual(hop.src.id, "node6", "Correct first iteration - source")
        self.assertEqual(hop.dst.id, "node5", "Correct first iteration - destination")
        hop = next(it2)
        self.assertEqual(hop.src.id, "node5", "Correct parent jump - source")
        self.assertEqual(hop.dst.id, "node4", "Correct parent jump - destination")
        next(it2)
        hop = next(it2)
        self.assertEqual(hop.src.id, "node3", "Correct second parent jump - source")
        self.assertEqual(hop.dst.id, "node2", "Correct second parent jump - destination")
        next(it2)
        self.assertFalse(it2.has_next(), "Reverse iterator has no elements left")
        with self.assertRaises(StopIteration):
            next(it2)

    def test_0002_message_traversal(self):
        # Scenario: we have an attacker node, two routers and three targets linked in this fashion: A-S1-S2-T1
        #                                                                                                   \T2
        #                                                                                                   \T3
        # The attacker establishes a session from A to T1 and from this session establishes another to T2 and
        # from this one sends a message to T3.
        # An entire environment must be constructed for this to test, because the environment shuffles around
        # messages.
        env = Environment(pause_on_response=["attacker_node.attacker1"])
        proxy = EnvironmentProxy(env, "attacker_node")
        Policy().reset()

        # We discard testing all authorizations for this scenario
        all_root = Authorization("root", [], None, AccessLevel.ELEVATED, "1111")
        Policy().add_authorization(all_root)

        # Create a simple attacker
        attacker_node = Node("attacker_node")
        attacker = SimpleAttacker("attacker1", env=proxy)
        attacker_node.add_service(attacker)

        # Create three identical passive nodes with ssh enabled
        target1 = Node("target1", ip="192.168.1.2", mask="255.255.255.0")
        target1.add_interface(Interface(ip="192.168.2.2", mask="255.255.255.0"))
        target2 = Node("target2", ip="192.168.2.3", mask="255.255.255.0")
        target2.add_interface(Interface(ip="192.168.3.3", mask="255.255.255.0"))
        target3 = Node("target3", ip="192.168.3.4", mask="255.255.255.0")

        ssh_service = PassiveService("ssh", owner="ssh")
        ssh_service.set_enable_session(True)
        ssh_service.set_session_access_level(AccessLevel.LIMITED)

        target1.add_service(ssh_service)
        target2.add_service(ssh_service)
        target3.add_service(ssh_service)

        # Create two routers - the explicit declarations on routers specify which network they are willing to route
        #                       for messages coming from the outside
        # TODO: Much will change, if we ever implement the notion of firewall
        router1 = Router("router1", env)
        router1_port = router1.add_port("192.168.0.1", "255.255.255.0")
        router2 = Router("router2", env)
        router2_port = router2.add_port("192.168.1.1", "255.255.255.0")

        # Add all nodes to the environment
        env.add_node(attacker_node)
        env.add_node(router1)
        env.add_node(router2)
        env.add_node(target1)
        env.add_node(target2)
        env.add_node(target3)

        # Connect routers
        env.add_connection(router1, router2, router1_port, router2_port)
        router1.add_route(Route(IPNetwork("192.168.1.1/255.255.255.0"), router1_port))
        router2.add_route(Route(IPNetwork("192.168.0.1/255.255.255.0"), router2_port))

        # Route to test dropping of unaccepted packets
        router1.add_route(Route(IPNetwork("192.168.2.1/255.255.255.0"), router1_port))

        # Connect the nodes to routers
        env.add_connection(router1, attacker_node, net="192.168.0.1/24")
        # Targets 1 and 2 are connected twice using two different ports
        # It does not have to be specified explicitly, it is here for better readability
        env.add_connection(router2, target1, target_port_index=0)
        env.add_connection(router2, target1, target_port_index=1)
        env.add_connection(router2, target2, target_port_index=0)
        env.add_connection(router2, target2, target_port_index=1)
        env.add_connection(router2, target3)

        # Get correct actions
        actions = {}
        action_list = ActionList().get_actions("rit")
        for action in action_list:
            actions[action.tags[0].name] = action

        action = actions["rit:ensure_access:command_and_control"]

        # Test direct connection to an inaccessible node
        attacker.execute_action("192.168.2.2", "ssh", action, session=None, authorization=all_root)

        env.run()

        response = attacker.get_last_response()
        s = response.session

        self.assertEqual(response.status.origin, StatusOrigin.NETWORK, "Got response from network")
        self.assertEqual(response.status.value, StatusValue.FAILURE, "host unreachable")

        # Correct via multiple sessions

        attacker.execute_action("192.168.1.2", "ssh", action, session=None, authorization=all_root)

        env.resume()

        response = attacker.get_last_response()
        s = response.session

        self.assertTrue(response.session, "Received a session back")

        session1 = Session("root", None, path=[Hop(Endpoint(id='attacker_node', port=0), Endpoint(id='router1', port=1)), Hop(Endpoint(id='router1', port=0), Endpoint(id='router2', port=0)), Hop(Endpoint(id='router2', port=1), Endpoint(id='target1', port=0))])
        self.assertEqual(s, session1)

        attacker.execute_action("192.168.2.3", "ssh", action, session=s, authorization=all_root)

        env.resume()

        response = attacker.get_last_response()
        s = response.session

        self.assertTrue(response.session, "Received a session back")

        session2 = Session("root", session1, path=[Hop(src=Endpoint(id='target1', port=1), dst=Endpoint(id='router2', port=2)), Hop(src=Endpoint(id='router2', port=3), dst=Endpoint(id='target2', port=0))])
        self.assertEqual(s, session2)

        # Now to just try running an action over two sessions
        action = actions["rit:active_recon:service_discovery"]
        attacker.execute_action("192.168.3.4", "ssh", action, session=s, authorization=all_root)

        env.resume()

        response = attacker.get_last_response()
        self.assertEqual(response.content, ["ssh"])


class TestRouting(unittest.TestCase):

    def test_0000_routing(self):

        env = Environment()

        router1 = Router("router1", env)
        router1_port = router1.add_port("10.0.0.0", "255.255.0.0")

        # Technically, the last route is all tha is needed, but this is to test overlapping and correct ordering
        router1.add_route(Route(IPNetwork("10.1.0.0/30"), router1_port))
        router1.add_route(Route(IPNetwork("10.1.0.0/26"), router1_port, metric=30))
        router1.add_route(Route(IPNetwork("10.1.0.0/22"), router1_port))
        router1.add_route(Route(IPNetwork("10.1.0.0/16"), router1_port))
        router1.add_route(Route(IPNetwork("10.1.5.4/16"), router1_port))
        router1.add_route(Route(IPNetwork("10.1.5.4/16"), router1_port))

        routes = router1.list_routes()
        self.assertEqual(routes[0].net.prefixlen, 26, "Correctly prioritized metric")
        self.assertEqual(routes[1].net.prefixlen, 30, "Correctly prioritized prefixlen")
        self.assertEqual(routes[5].net.ip, IPAddress("10.1.5.4"), "Correctly ordered IP addresses")


if __name__ == '__main__':
    unittest.main()

