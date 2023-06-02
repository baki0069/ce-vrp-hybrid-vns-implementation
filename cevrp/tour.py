import random
from copy import deepcopy
from typing import Iterable

from cevrp.vehicle import Vehicle
from cevrp.cost_types import CostTypes
from cevrp.node import *


def is_collection_instance(collection: Iterable, collection_type, element_type) -> bool:
    return isinstance(collection, collection_type) and any(isinstance(el, element_type) for el in collection)


class Tour(Iterable):
    id = 1

    def __init__(self, nodes: list[Node] | tuple[Node, Node]):
        self.id = Tour.id

        if is_collection_instance(nodes, list, Node):
            self.nodes = nodes
        elif is_collection_instance(nodes, tuple, Node):
            self.nodes = [n for n in nodes]
        elif isinstance(nodes, list) and all(is_collection_instance(el, tuple, Node) for el in nodes):
            self.nodes = [n for n in nodes if n not in self.nodes]
        else:
            ValueError("Illegal node type.")

        Tour.id += 1

    def __iter__(self):
        yield from self.nodes

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        tour_string = " - ".join([str(each) for each in self.nodes])
        return tour_string

    def __eq__(self, other):
        if isinstance(other, Tour):
            return self.nodes == other.nodes
        if isinstance(other, list) and all(isinstance(el, Node) for el in other):
            return other == self.nodes

    def __lt__(self, other):
        return len(self.nodes) < other

    def __gt__(self, other):
        return len(self.nodes) > other

    def __len__(self) -> int:
        return len(self.nodes)

    def __add__(self, other):
        if isinstance(other, Tour):
            new_nodes = self.nodes[:-1] + other.nodes[1:]
            return Tour(new_nodes)
        else:
            raise TypeError(f"Unsupported operand type for +: 'Tour' and '{type(other).__name__}'")

    def __getitem__(self, item_indicator):
        if isinstance(item_indicator, int):
            return self.nodes[item_indicator]
        if isinstance(item_indicator, Node):
            return self.nodes[self.nodes.index(item_indicator)]
        if isinstance(item_indicator, slice):
            return self.nodes[item_indicator.start:item_indicator.stop:item_indicator.step]
        if isinstance(item_indicator, tuple) and all(isinstance(n, Node) for n in item_indicator):
            try:
                return self.get_edges()[self.get_edges().index(item_indicator)]
            except Exception:
                a: tuple[Node, Node] = item_indicator
                raise LookupError(f"Tuple ({a[0].node_id}, {a[1].node_id}) is not an edge in {self}")

        else:
            raise TypeError(f"Unsupported operand type: [{type(item_indicator).__name__}]")

    def __setitem__(self, key, value):
        # convert value-type to list[Node]
        if isinstance(value, Tour):
            value = value.nodes
        if is_collection_instance(value, tuple, Node):
            value = [v for v in value]

        # convert key-type to list[int]
        if isinstance(key, Tour):
            key = [self.nodes.index(n) for n in self if n in key]
        if is_collection_instance(key, tuple, int):
            key = [k for k in key]
        if isinstance(key, slice):
            key = [s for s in range(
                key.indices(len(self))[0],
                key.indices(len(self))[1],
                key.indices(len(self))[2],
            )]
        if isinstance(key, Node):
            key = [self.nodes.index(n) for n in self if n == key][0]
        if is_collection_instance(key, tuple, Node) or is_collection_instance(key, list, Node):
            key = [self.nodes.index(n) for n in self if n in key]

        if is_collection_instance(key, list, int):
            if is_collection_instance(value, list, Node):
                self.__setitem__handle_node_list_value(key, value)
                return
            elif isinstance(value, Node):
                self.__setitem__handle_node_list_value(key, [value for _ in range(len(key))])
                return

        # case key is int and value is singleton Node
        if isinstance(key, int) and isinstance(value, Node):
            self.nodes[key] = value
            return

        raise TypeError(f"{type(key)} or {type(value)} is not a valid operand for {self.__setitem__}.")

    def __setitem__handle_node_list_value(self, key, value):
        diff = set([abs(k1 - k2) for (k1, k2) in zip(key[:-1], key[1:])])
        if len(set(diff)) != 1 and len(key) != 1:
            raise IndexError(f"Elements of iterator index {key} need to be equidistant.")
        if len(set(diff)) == 1:
            increment = diff.pop()
        else:
            increment = key[0]
        if key[0] > key[-1]:
            increment = -increment
        for index, key_i in enumerate(range(key[0], key[-1] + 1, increment)):
            if index >= len(value):
                break
            self.nodes[key_i] = value[index]

    def __hash__(self):
        return self.id

    def remove(self, node):
        if is_collection_instance(node, list, Node):
            for n in node:
                self.nodes.remove(n)
        if isinstance(node, Node):
            self.nodes.remove(node)
        if isinstance(node, int):
            self.nodes.remove(self[node])

    def get_next_node(self, node: Node, amount: int = 1) -> Node:
        return self[(self.nodes.index(node) + amount) % len(self)]

    def get_next_edge(self, edge: tuple[Node, Node], amount: int = 1) -> tuple[Node, Node]:
        edges = self.get_edges()
        return edges[(edges.index(edge) + amount) % len(edges)]

    def get_previous_node(self, node: Node, amount: int = 1) -> Node:
        return self.get_next_node(node, -amount)

    def get_previous_edge(self, node: tuple[Node, Node], amount: int = 1) -> tuple[Node, Node]:
        return self.get_next_edge(node, -amount)

    def get_costs_of_tour(self, vehicle: Vehicle, battery_threshold: float) -> dict[CostTypes, float]:
        ref = +vehicle
        costs = {
            CostTypes.DISTANCE: self.get_total_distance(),
            CostTypes.BATTERY_RECHARGING: self.get_battery_recharging_costs(ref, battery_threshold),
            CostTypes.SERVICE_TIME: self.get_total_service_time(),
            CostTypes.DEMAND: self.get_total_demand()
        }

        costs[CostTypes.TOTAL] = \
            costs[CostTypes.DISTANCE] \
            + costs[CostTypes.BATTERY_RECHARGING] \
            + costs[CostTypes.SERVICE_TIME] \
            + costs[CostTypes.DEMAND]

        return costs

    def get_edges(self) -> list[tuple[Node, Node]]:
        return [first + second
                for (first, second)
                in zip(self.nodes, self.nodes[1:])
                ]

    def get_total_distance(self):
        return sum(abs(e[0] - e[1]) for e in self.get_edges())

    def get_battery_recharging_costs(self, vehicle: Vehicle, battery_threshold: float):
        # calculate battery recharging costs (time spent at customer to refresh battery charge)
        # if the travel distance between any two nodes brings the battery charge level
        # below the threshold.
        # If battery charge level stays above threshold despite the distance traveled,
        # the current battery charge value is persisted for the next iteration.
        vehicle = +vehicle
        total_battery_recharge_cost = 0

        edges = self.get_edges()
        for edge in edges:
            vehicle = vehicle - edge  # v - tuple[node,node] -> v (dim. battery cap.)
            if vehicle.current_battery_level < battery_threshold:
                # Battery must be fully recharged
                battery_recharge_amount = vehicle.battery.capacity - vehicle.current_battery_level
                total_battery_recharge_cost += battery_recharge_amount / vehicle.battery.charging_rate
                vehicle = +vehicle  # unary recharge operator
        return total_battery_recharge_cost

    def get_subtour_distance(self, node: Node, symmetric_length: int = 1):
        index = self.nodes.index(node)
        # slice operator <=> right-open-interval (e.g. [2; 5) == {2, 3, 4})
        subtour = Tour(self[index - symmetric_length:index + symmetric_length + 1])
        return subtour.get_total_distance()

    # return indices of chain of subsequent nodes
    def get_index_slice_of_node_chain(self, nodes: 'Tour') -> slice:
        indices = [index for index, node in enumerate(self) if node in nodes]
        if len(indices) != 1 and all(abs(first - second) != 1 for (first, second) in zip(indices[:-1], indices[1:])):
            raise ValueError(f'{nodes} is not a chain of subsequent nodes.')
        return slice(min(indices), max(indices) + 1)

    def get_indices_of(self, nodes: 'Tour') -> list[int]:
        depot = Node.create_depot()
        indices = [index for index, node in enumerate(self) if node in nodes and node != depot]
        if depot not in nodes:
            return indices
        if depot == nodes[0]:
            return [0] + indices
        if depot == nodes[-1]:
            return indices + [len(self) - 1]
        else:
            ValueError("I don't know how to deal with intra-tour depots, yet.")

    def get_total_service_time(self):
        return sum(n.service_time for n in self)

    def get_total_demand(self):
        return sum(n.demand for n in self)

    def get_random_intertour_node(self):
        return self[random.randint(1, len(self)-2)]

    def get_manual_copy(self):
        return Tour(
            [Node(n.node_id, n.demand, n.service_time, n.x, n.y, n.distance_calculator)
             for n in self]
        )

    @classmethod
    def empty(cls):
        return Tour([])
