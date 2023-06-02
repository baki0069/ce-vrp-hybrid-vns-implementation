import unittest
from math import sqrt

from cevrp.cost_types import CostTypes
from cevrp.node import Node
from cevrp.tour import Tour
from cevrp.vehicle import Vehicle


class TourTests(unittest.TestCase):
    def setUp(self):
        n1 = []
        n2 = []
        self.depot = [Node.create_depot()]
        for i in range(1, 10):
            n1.append(Node(i, i, i, i, i))
        for i in range(11, 20):
            n2.append(Node(i, i, i, i, i))
        self.n1 = n1
        self.n2 = n2
        self.t1 = Tour(self.depot + n1 + self.depot)
        self.t2 = Tour(self.depot + n2 + self.depot)

    def test__eq__(self):
        # right-hand operand [Tour]
        self.assertFalse(self.t1 == self.t2)

        # right-hand operand [list[Node]]
        self.assertTrue(self.t1 == self.depot + self.n1 + self.depot)
        self.assertFalse(self.t1 == self.n1)

    def test__len__(self):
        self.assertEqual(len(self.t1), 11)
        self.assertNotEqual(len(self.t1), 12)

    def test__add__(self):
        # right-hand operand [Tour]
        merged = self.depot + self.n1 + self.n2 + self.depot
        self.assertEqual(self.t1 + self.t2, merged)

    def test__getitem__(self):
        depot: Node = self.depot[0]
        # index operand [int]
        self.assertEqual(self.t1[0], depot)
        self.assertEqual(self.t1[2], self.n1[1])
        self.assertNotEqual(self.t1[2], self.n1[2])

        # index operand [Node]
        self.assertEqual(self.t1[self.n1[3]], self.n1[3])
        self.assertEqual(self.t1[depot], depot)

        # index operand [slice]
        self.assertEqual(self.t1[2:5], self.n1[1:4])
        self.assertNotEqual(self.t1[2:4], self.n1[1:4])

        # index operand [tuple[Node]]
        edges = self.t1.get_edges()
        expectation = self.t1.get_edges()[edges.index((depot, self.n1[0]))]
        self.assertEqual(self.t1[(depot, self.n1[0])], expectation)
        self.assertRaises(LookupError, self.t1.__getitem__, (depot, self.n1[1]))

    def test__setitem__(self):
        dp = Node.create_depot()
        with self.subTest("KEY: LIST[INT], VALUE: LIST[NODE] - SAME CARDINALITY"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p2 = [self.n2[1], self.n2[2], self.n2[3]]
            t1[[1, 3, 5]] = p2
            expectation = [dp, self.n2[1], self.n1[2], self.n2[2], self.n1[4], self.n2[3]]
            self.assertEqual(t1, expectation)

        with self.subTest("KEY: LIST[INT], VALUE: LIST[NODE] - |KEY| > |VALUE|"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p2 = [self.n2[1], self.n2[2], self.n2[3], self.n2[4]]
            t1[[1, 3, 5]] = p2
            expectation = [dp, self.n2[1], self.n1[2], self.n2[2], self.n1[4], self.n2[3]]
            self.assertEqual(t1, expectation)

        with self.subTest("KEY: LIST[INT], VALUE: LIST[NODE] - |KEY| < |VALUE|"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p2 = [self.n2[1], self.n2[2]]
            t1[[1, 3, 5]] = p2
            expectation = [dp, self.n2[1], self.n1[2], self.n2[2], self.n1[4], dp]
            self.assertEqual(t1, expectation)

        with self.subTest("KEY: TUPLE[INT], VALUE: SINGLETON_INT"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p = Node(69, 69, 69, 69, 69)
            t1[1, 3, 5] = p
            expectation = [dp, p, self.n1[2], p, self.n1[4], p]
            self.assertEqual(t1, expectation)

        with self.subTest("KEY: SLICE, VALUE: LIST[NODE] - |KEY| < |VALUE|"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p2 = [self.n2[1], self.n2[2]]
            t1[-1:1:-1] = p2
            expectation = t1[0:4] + [p2[1], p2[0]]
            self.assertEqual(t1, expectation)

        with self.subTest("KEY: SLICE, VALUE: SINGLETON_INT"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p = Node(69, 69, 69, 69, 69)
            t1[1:4:2] = p
            expectation = [dp, p, self.n1[2], p, self.n1[4], dp]
            self.assertEqual(t1, expectation)

        with self.subTest("KEY: NODE, VALUE: any"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p = Node(69, 69, 69, 69, 69)
            t1[self.n1[2]] = p
            expectation = [dp, self.n1[1], p, self.n1[3], self.n1[4], dp]
            self.assertEqual(t1, expectation)

        with self.subTest("KEY: LIST[NODE], VALUE: any"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p = Node(69, 69, 69, 69, 69)
            t1[[self.n1[2], self.n1[3]]] = p
            expectation = [dp, self.n1[1], p, p, self.n1[4], dp]
            self.assertEqual(t1, expectation)

        with self.subTest("KEY: TUPLE[NODE, NODE], VALUE: any"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p = Node(69, 69, 69, 69, 69)
            t1[self.n1[2], self.n1[3]] = p
            expectation = [dp, self.n1[1], p, p, self.n1[4], dp]
            self.assertEqual(t1, expectation)

        with self.subTest("KEY: TOUR, VALUE: any"):
            t1 = Tour([dp, self.n1[1], self.n1[2], self.n1[3], self.n1[4], dp])
            p = Node(69, 69, 69, 69, 69)
            t1[Tour([self.n1[2], self.n1[3]])] = p
            expectation = [dp, self.n1[1], p, p, self.n1[4], dp]
            self.assertEqual(t1, expectation)

        with self.subTest("Raise error if invalid operands"):
            t1 = Tour([dp, dp, dp])
            self.assertRaises(TypeError, t1.__setitem__, "abc", dp)
            self.assertRaises(TypeError, t1.__setitem__, [1, 2, 3], "abc")
            self.assertRaises(TypeError, t1.__setitem__, "abc", "abc")

    def test_tour_should_get_next_node(self):
        self.assertEqual(self.t1.get_next_node(self.t1[3]), self.t1[4])

    def test_tour_should_get_next_edge(self):
        self.assertEqual(self.t1.get_next_edge((self.t1[3], self.t1[4])), self.t1.get_edges()[4])

    def test_tour_should_get_previous_node(self):
        self.assertEqual(self.t1.get_previous_node(self.t1[3]), self.t1[2])

    def test_tour_should_get_previous_edge(self):
        self.assertEqual(self.t1.get_previous_edge((self.t1[3], self.t1[4])), self.t1.get_edges()[2])

    def test_costs_of_tour(self):
        dp = Node.create_depot()
        veh = Vehicle(1, 10, 50, 5, 5, 50)
        tour = Tour([dp, Node(1, 2, 2, 1, 1), Node(2, 2, 2, 3, -1), dp])
        lengths = [sqrt(2), sqrt(8), sqrt(10)]
        total_distance = sum(lengths)
        result = tour.get_costs_of_tour(veh, 40)
        total_battery_recharge_cost = 7.405  # calculated by hand
        service_times = sum(n.service_time for n in tour)
        demand = sum(n.demand for n in tour)
        self.assertAlmostEqual(result[CostTypes.DISTANCE], total_distance, delta=0.01)
        self.assertAlmostEqual(result[CostTypes.BATTERY_RECHARGING], total_battery_recharge_cost, delta=0.01)
        self.assertEqual(result[CostTypes.SERVICE_TIME], service_times)
        self.assertEqual(result[CostTypes.DEMAND], demand)

    def test_get_random_intertour_node(self):
        dp = Node.create_depot()
        n1 = Node(1, 2, 2, 1, 1)
        n2 = Node(2, 2, 2, 3, -1)
        tour = Tour([dp, n1, n2, dp])
        r = []
        for _ in range(1000):
            r.append(tour.get_random_intertour_node())
        self.assertAlmostEqual(r.count(n1), 500, delta=50)
        self.assertAlmostEqual(r.count(n2), 500, delta=50)
