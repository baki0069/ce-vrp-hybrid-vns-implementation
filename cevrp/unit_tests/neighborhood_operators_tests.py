import unittest
from cevrp.vnd.neighborhood_operators import NeighborhoodOperators, NeighborhoodOperatorsImpl
from cevrp.vnd.neighborhood_data import NeighborhoodData
from cevrp.node import Node
from cevrp.savings_calculator import SavingsCalculator
from cevrp.tour import Tour
from cevrp.vehicle import Vehicle


class NeighborhoodOperatorsTests(unittest.TestCase):
    def setUp(self):
        self.nodes = []
        for i in range(1, 20):
            binary = bin(i % 4)[2:].zfill(2)
            x_flag, y_flag = bool(int(binary[0])), bool(int(binary[1]))
            self.nodes.append(Node(i, 1, 1, -i if y_flag else i, -i if x_flag else i))

    def test_cross_exchange(self):
        n = self.nodes
        d = Node.create_depot()
        t1 = Tour([d, n[0], n[1], n[2], d])
        t2 = Tour([d, n[3], n[4], n[5], d])
        v = Vehicle(1, 1000, 1000, 1, 1, 100)
        with self.subTest("Should not allow both subtours to have one-cardinality"):
            s1 = t1[2]
            s2 = t2[1]
            data = NeighborhoodData(t1, t2, s1, s2, v, 1000, SavingsCalculator.get_savings)
            self.assertRaises(ValueError, NeighborhoodOperators.CROSS_EXCHANGE, data)
        with self.subTest("Should cross exchange"):
            s1 = t1[2:4]
            s2 = t2[1:3]
            data = NeighborhoodData(t1, t2, s1, s2, v, 1000, SavingsCalculator.get_savings)
            t1, t2 = NeighborhoodOperators.CROSS_EXCHANGE(data)
            self.assertEqual(t1, Tour([d, n[0], n[3], n[4], d]))
            self.assertEqual(t2, Tour([d, n[1], n[2], n[5], d]))
        with self.subTest("Should handle unequal cardinalities [sub1 > sub2]"):
            t1 = Tour([d, n[0], n[1], n[2], d])
            t2 = Tour([d, n[3], n[4], n[5], d])
            s1 = t1[1:4]
            s2 = t2[1]
            data = NeighborhoodData(t1, t2, s1, s2, v, 1000, SavingsCalculator.get_savings)
            t1, t2 = NeighborhoodOperators.CROSS_EXCHANGE(data, True)
            self.assertEqual(t1, Tour([d, n[3], d]))
            self.assertEqual(t2, Tour([d, n[0], n[1], n[2], n[4], n[5], d]))
        with self.subTest("Should handle unequal cardinalities [sub1 < sub2]"):
            t1 = Tour([d, n[0], n[1], n[2], d])
            t2 = Tour([d, n[3], n[4], n[5], d])
            s1 = t1[1:3]
            s2 = t2[1:4]
            data = NeighborhoodData(t1, t2, s1, s2, v, 1000, SavingsCalculator.get_savings)
            t1, t2 = NeighborhoodOperators.CROSS_EXCHANGE(data, True)
            self.assertEqual(t2, Tour([d, n[3], n[4], n[5], n[2], d]))
            self.assertEqual(t1, Tour([d, n[0], n[1], d]))

    def test_get_random_subtours(self):
        n = self.nodes
        d = Node.create_depot()
        t = Tour([d, n[0], n[1], n[2], d])
        for i in range(1, 5):
            with self.subTest(length=i):
                s1, s2 = NeighborhoodOperatorsImpl.get_random_tour_sections(t, i)
                self.assertTrue(s in t.get_edges() for s in s1.get_edges())
                self.assertTrue(s in t.get_edges() for s in s2.get_edges())
                self.assertNotEqual(s1, s2)

    def test_get_random_subtour(self):
        n = self.nodes
        d = Node.create_depot()
        t = Tour([d, n[0], n[1], n[2], d])
        for i in range(1, 5):
            with self.subTest(length=i):
                s1 = NeighborhoodOperatorsImpl.get_random_tour_section(t, i)
                self.assertTrue(s in t.get_edges() for s in s1.get_edges())
