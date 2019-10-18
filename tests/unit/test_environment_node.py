import unittest

from environment.node import Node


class TestNodeStructures(unittest.TestCase):

    def test_node_addressing(self):
        n1 = Node("switch1", "Switch", "192.168.0.1", "255.255.255.0")
        n2 = Node("node1", "Node", "192.168.0.3", "255.255.255.0")

        self.assertEqual(n1.ip, "192.168.0.1")
        self.assertEqual(n1.mask, "255.255.255.0")
        self.assertEqual(n1.gateway, n1.ip)
        self.assertEqual(n2.gateway, n1.ip)


if __name__ == '__main__':
    unittest.main()
