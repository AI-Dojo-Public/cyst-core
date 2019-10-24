import unittest

from attackers.simple import SimpleAttacker
from environment.access import Authorization, AccessLevel, Policy
from environment.action import ActionList, Action
from environment.environment import Environment
from environment.message import Request, Response
from environment.network import Session, Switch
from environment.node import PassiveNode, Service


class TestSessions(unittest.TestCase):

    def test_0000_single_session(self):
        with self.assertRaises(Exception):
            s0 = Session(owner="", path=["node1", "node2", "node3"])

        s1 = Session("user1", path=["node1", "node2", "node3"])
        it = s1.get_forward_iterator()

        self.assertTrue(it.has_next(), "Forward iterator has some elements")
        self.assertEqual(next(it), "node1", "Correct first iteration")
        self.assertEqual(next(it), "node2", "Correct second iteration")
        self.assertEqual(next(it), "node3", "Correct third iteration")
        self.assertFalse(it.has_next(), "Forward iterator has no elements left")
        with self.assertRaises(StopIteration):
            next(it)

    def test_0001_multiple_sessions(self):
        s1 = Session("user1", path=["node1", "node2", "node3"])
        s2 = Session("user1", parent=s1, path=["node3", "node4", "node5"])
        s3 = Session("user1", parent=s2, path=["node5", "node6"])

        it = s3.get_forward_iterator()
        self.assertTrue(it.has_next(), "Forward iterator has some elements")
        self.assertEqual(next(it), "node1", "Correct first iteration")
        next(it)
        next(it)
        self.assertEqual(next(it), "node4", "Correct parent jump")
        next(it)
        self.assertEqual(next(it), "node6", "Correct parent jump and path addition")
        self.assertFalse(it.has_next(), "Forward iterator has no elements left")
        with self.assertRaises(StopIteration):
            next(it)

        with self.assertRaises(Exception):
            s4 = Session("user2", parent=s3, path=["node7", "node8"])

        with self.assertRaises(Exception):
            s5 = Session("user1", parent=s1, path=["node3"])

        it2 = s3.get_reverse_iterator()
        self.assertTrue(it2.has_next(), "Reverse iterator has some elements")
        self.assertEqual(next(it2), "node6", "Correct first iteration")
        self.assertEqual(next(it2), "node5", "Correct second iteration and parent jump")
        next(it2)
        self.assertEqual(next(it2), "node3", "Correct fourth iteration and parent jump")
        next(it2)
        next(it2)
        self.assertFalse(it2.has_next(), "Reverse iterator has no elements left")
        with self.assertRaises(StopIteration):
            next(it2)

    def test_0002_message_traversal(self):
        # Scenario: we have an attacker node, two switches and three targets linked in this fashion: A-S1-S2-T1
        #                                                                                                   \T2
        #                                                                                                   \T3
        # The attacker establishes a session from A to T1 and from this session establishes another to T2 and
        # from this one sends a message to T3.
        # An entire environment must be constructed for this to test, because the environment shuffles around
        # messages.
        env = Environment(pause_on_response=["attacker1"])
        Policy().reset()

        # We discard testing all authorizations for this scenario
        all_root = Authorization("root", [], None, AccessLevel.ELEVATED, "1111")
        Policy().add_authorization(all_root)

        # Create a simple attacker
        attacker = SimpleAttacker("attacker1", env=env)

        # Create three identical passive nodes with ssh enabled
        target1 = PassiveNode("target1", ip="192.168.1.2", mask="255.255.255.0")
        target2 = PassiveNode("target2", ip="192.168.1.3", mask="255.255.255.0")
        target3 = PassiveNode("target3", ip="192.168.1.4", mask="255.255.255.0")

        ssh_service = Service("ssh")
        ssh_service.set_enable_session(True)
        ssh_service.set_session_access_level(AccessLevel.LIMITED)

        target1.add_service(ssh_service)
        target2.add_service(ssh_service)
        target3.add_service(ssh_service)

        # Create two switches
        switch1 = Switch("switch1", "192.168.0.1", "255.255.255.0", env)
        switch2 = Switch("switch2", "192.168.1.1", "255.255.255.0", env)

        # Add all nodes to the environment
        env.add_node(attacker)
        env.add_node(switch1)
        env.add_node(switch2)
        env.add_node(target1)
        env.add_node(target2)
        env.add_node(target3)

        # Connect switches
        switch1.connect_switch(switch2)

        # Connect the nodes to switches
        switch1.connect_node(attacker)
        switch2.connect_node(target1)
        switch2.connect_node(target2)
        switch2.connect_node(target3)

        # Get correct actions
        actions = {}
        action_list = ActionList().get_actions("rit")
        for action in action_list:
            actions[action.tags[0].name] = action

        action = actions["rit:ensure_access:command_and_control"]
        attacker.execute_action("192.168.1.2", "ssh", action, session=None, authorization=all_root)

        env.run()

        response = attacker.get_last_response()
        s = response.session

        self.assertTrue(response.session, "Received a session back")

        session1 = Session("root", None, ["192.168.0.2", "192.168.0.1", "192.168.1.1", "192.168.1.2"])
        self.assertEqual(s, session1)

        attacker.execute_action("192.168.1.3", "ssh", action, session=s, authorization=all_root)

        env.resume()

        response = attacker.get_last_response()
        s = response.session

        self.assertTrue(response.session, "Received a session back")

        session2 = Session("root", session1, ["192.168.1.2", "192.168.1.1", "192.168.1.3"])
        self.assertEqual(s, session2)

        # Now to just try running an action over two sessions
        action = actions["rit:active_recon:service_discovery"]
        attacker.execute_action("192.168.1.4", "ssh", action, session=s, authorization=all_root)

        env.resume()

        response = attacker.get_last_response()
        self.assertEqual(response.content, ["ssh"])


if __name__ == '__main__':
    unittest.main()
