from typing import Callable

from cevrp.node import Node
from cevrp.tour import Tour
from cevrp.vehicle import Vehicle


class NeighborhoodData:
    def __init__(
            self,
            tour1: Tour,
            tour2: Tour,
            vehicle: Vehicle,
            battery_threshold: float,
            savings_calc: Callable[[Tour, Tour, Vehicle, float], float | int],
            tour_1_section_indices=None,
            tour_2_section_indices=None,
            tour_1_section_nodes=None,
            tour_2_section_nodes=None
    ):
        self.tour_1 = tour1
        self.tour_2 = tour2
        self.tour_1_section_indices = tour_1_section_indices
        self.tour_2_section_indices = tour_2_section_indices

        if isinstance(tour_1_section_indices, Node):
            self.tour_1_section_indices = [self.tour_1.nodes.index(t) for t in self.tour_1 if t == tour_1_section_indices]
        if isinstance(tour_2_section_indices, Node):
            self.tour_2_section_indices = [self.tour_2.nodes.index(t) for t in self.tour_2 if t == tour_2_section_indices]

        self.tour_1_section_nodes = tour_1_section_nodes
        self.tour_2_section_nodes = tour_2_section_nodes

        self.vehicle = vehicle
        self.battery_threshold = battery_threshold
        self.savings_calc = savings_calc

    def calculate_savings(self, old_tour: Tour, modified_tour: Tour):
        return self.savings_calc(old_tour, modified_tour, self.vehicle, self.battery_threshold)

    def apply_and_swap_on_savings(
            self,
            slice_1: slice | tuple,
            slice_2: slice | tuple,
            tour_1_modification,
            tour_2_modification
    ):
        tour_1_modified = self.tour_1.get_manual_copy()
        tour_2_modified = self.tour_2.get_manual_copy()

        if isinstance(slice_1, slice):
            tour_1_modified.slice_replace(slice_1, tour_1_modification)
        else:
            tour_1_modified.list_replace(slice_1, tour_1_modification)

        if isinstance(slice_2, slice):
            tour_2_modified.slice_replace(slice_2, tour_2_modification)
        else:
            tour_2_modified.list_replace(slice_2, tour_2_modification)

        savings_1 = self.calculate_savings(self.tour_1, tour_1_modified)
        savings_2 = self.calculate_savings(self.tour_2, tour_2_modified)
        if savings_1 + savings_2 > 0:
            self.tour_1 = tour_1_modified
            self.tour_2 = tour_2_modified

        return self.tour_1, self.tour_2
