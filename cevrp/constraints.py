import types
from enum import Enum
from typing import Callable, Any

from cevrp.node import Node
from cevrp.tour import Tour
from cevrp.vehicle import Vehicle


class ConstraintValidationStrategy:
    def __init__(
            self,
            constraint_function,
            tour: Tour,
            ref_vhcl: Vehicle,
            battery_threshold: int
    ):
        self.tour = tour
        self.vehicle = +ref_vhcl
        self.battery_threshold = battery_threshold
        self.is_valid = types.MethodType(constraint_function[1], self)

    def is_valid(self):
        pass


def check_depot_count(self: ConstraintValidationStrategy):
    return self.tour.nodes.count(Node.create_depot()) == 2


def check_tour_capacity(self: ConstraintValidationStrategy):
    return sum(node.demand for node in self.tour) <= self.vehicle.commodity_capacity


def check_total_tour_distance(self: ConstraintValidationStrategy):
    edges = self.tour.get_edges()
    tour_distance = sum(
        e[0] - e[1]
        for e
        in edges
    )
    return tour_distance <= self.vehicle.distance_threshold


def check_battery_capacity_for_tour(self: ConstraintValidationStrategy):
    edges = self.tour.get_edges()
    tour_battery_charges = [
        (e[0] - e[1]) * self.vehicle.battery.consumption_rate
        for e
        in edges
    ]

    return all(
            charge <= self.battery_threshold
            for charge
            in tour_battery_charges
    )

    # ADD CONSTRAINT:
        # CHECK IF TOUR'S SECTIONS OF CRITICAL LENGTH
        # ARE SUBORDINATE TO BATTERY CAPACITY CONSTRAINT

    # if any()


class Constraints(Enum):
    DEPOT_COUNT = 1, check_depot_count
    TOUR_CAPACITY = 2, check_tour_capacity
    TOTAL_DISTANCE = 3, check_total_tour_distance
    BATTERY_CAPACITY = 4, check_battery_capacity_for_tour

    def __init__(self, function: Callable[[Any], bool], num: int):
        self.executable = function
        self.num = num

