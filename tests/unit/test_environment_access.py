import unittest

from environment.access import Authorization, AccessLevel, Policy


class TestPolicy(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Access to services s1 and s2 on each node
        a1 = Authorization("id1", [], ["s1", "s2"], AccessLevel.ELEVATED)
        # Access to all services on node n1
        a2 = Authorization("id2", ["n1"], [], AccessLevel.ELEVATED)
        # Access to services s1 and s2 on nodes n1, n2, n3
        a3 = Authorization("id3", ["n1", "n2", "n3"], ["s1", "s2"], AccessLevel.ELEVATED)
        # Access to everything
        a4 = Authorization("id4", [], [], AccessLevel.ELEVATED)

        Policy().add_authorization(a1, a2, a3, a4)

    def test_add_authorization(self):

        stats = Policy().get_stats()

        self.assertEqual(stats.authorization_entry_count, 10, "Number of authorization entries")

    def test_decide(self):
        t1 = Authorization("id1", ["n1"], ["s1"], AccessLevel.LIMITED)

        self.assertTrue(Policy().decide("n1", "s1", AccessLevel.NONE, t1)[0], "Authorization with greater access level")
        self.assertTrue(Policy().decide("n1", "s1", AccessLevel.LIMITED, t1)[0], "Authorization with equal access level")
        self.assertFalse(Policy().decide("n1", "s1", AccessLevel.ELEVATED, t1)[0], "Authorization with lower access level")
        self.assertFalse(Policy().decide("n2", "s1", AccessLevel.NONE, t1)[0], "Authorization for wrong node")


if __name__ == '__main__':
    unittest.main()
