import math
from typing import Self

import numpy as np


class Node:
    def __init__(self, node_id, demand, service_time, x, y, distance_calculator=None):
        self.node_id = node_id
        self.demand = demand
        self.service_time = service_time
        self.x = x
        self.y = y
        if distance_calculator is None:
            self.distance_calculator = self.calculate_distance
        else:
            self.distance_calculator = distance_calculator

    def __eq__(self, other) -> bool:
        return self.node_id == other.node_id

    def __repr__(self):
        return self.__str__()

    def __str__(self) -> str:
        return f"{self.node_id} (d{self.demand}, st{self.service_time}, x{self.x}, y{self.y})"

    def __lt__(self, other) -> bool:
        if isinstance(other, Node):
            return self.node_id < other.node_id
        else:
            raise TypeError()

    def __sub__(self, other) -> float:
        return self.distance_calculator(self, other)

    def __add__(self, other) -> tuple[Self, Self]:
        if isinstance(other, Node):
            return self, other
        else:
            raise TypeError(f'Unexpected summand {type(other)}')

    def __hash__(self):
        return self.node_id

    def get_copy(self):
        return Node(
            self.node_id,
            self.demand,
            self.service_time,
            self.x,
            self.y,
            self.distance_calculator
        )

    @staticmethod
    def calculate_distance(node1, node2):
        distance = math.sqrt(abs(node2.x - node1.x) ** 2 + abs(node2.y - node1.y) ** 2)
        return distance

    @property
    def __class__(self):
        return Node

    @staticmethod
    def create_depot() -> 'Node':
        return Node(0, 0, 0, 0, 0)

    creation_index = 1

    @staticmethod
    def list_create(
            x_y_locations: list[tuple[float, float]],
            demands,
            service_times,
            distance_calculator=None
    ):
        if len(demands) < len(x_y_locations) and len(service_times) < len(x_y_locations):
            raise AssertionError(f'Need at least {len(x_y_locations)} demands and services time records.')

        nodes = []
        if isinstance(x_y_locations, list) and all(isinstance(loc, tuple) for loc in x_y_locations):
            for index, each in enumerate(x_y_locations):
                x, y = each
                demand, service_time = demands[index], service_times[index]
                nodes.append(Node(Node.creation_index, demand, service_time, x, y, distance_calculator))
                Node.creation_index += 1

        return nodes
