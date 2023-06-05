from enum import Enum
from typing import Callable
import time
import random

from cevrp.constraints import Constraints, ConstraintValidationStrategy
from cevrp.cost_types import CostTypes
from cevrp.tour import Tour
from cevrp.tour_plan import TourPlan
from cevrp.vehicle import Vehicle

from cevrp.vnd.neighborhood_data import NeighborhoodData


def time_convert(sec):
    minutes = sec // 60
    sec = sec % 60
    hours = minutes // 60
    minutes = minutes % 60
    return "{0}:{1}:{2}".format(int(hours), int(minutes), sec)


def exchange_and_apply_on_savings_different_cardinalities(tour_1, tour_2, sub_2, subtour_1_index_slice,
                                                          subtour_2_index_slice, calc_savings, skip_savings=False):
    tour_1_modified = tour_1.get_manual_copy()
    tour_2_modified = tour_2.get_manual_copy()

    overridden = tour_1_modified[subtour_1_index_slice]
    tour_1_modified.slice_replace(subtour_1_index_slice, sub_2)
    tour_1_modified.remove(overridden[len(sub_2):])
    tour_2_modified.slice_replace(subtour_2_index_slice, overridden)
    rest = len(overridden) - subtour_2_index_slice.stop + subtour_2_index_slice.start
    overridden = overridden[len(overridden) - rest:]
    for r in range(rest):
        tour_2_modified.nodes.insert(subtour_2_index_slice.stop + r, overridden[r])

    savings_1 = calc_savings(tour_1, tour_1_modified)
    savings_2 = calc_savings(tour_2, tour_2_modified)

    if savings_1 + savings_2 > 0 or skip_savings:
        tour_1 = tour_1_modified
        tour_2 = tour_2_modified

    return tour_1, tour_2


class NeighborhoodOperatorsImpl:
    # INTER-ROUTE-EXCHANGE
    @staticmethod
    def cross_exchange(data: NeighborhoodData, skip_savings=False):
        subtour_2_index_slice = data.tour_2.get_index_slice_of_node_chain(Tour(data.tour_2_section_nodes))
        subtour_1_index_slice = data.tour_1.get_index_slice_of_node_chain(Tour(data.tour_1_section_nodes))

        if len(data.tour_1_section_nodes) > len(data.tour_2_section_nodes):
            return exchange_and_apply_on_savings_different_cardinalities(
                data.tour_1,
                data.tour_2,
                data.tour_2_section_nodes,
                subtour_1_index_slice,
                subtour_2_index_slice,
                data.calculate_savings,
                skip_savings
            )
        if len(data.tour_2_section_nodes) > len(data.tour_1_section_nodes):
            return exchange_and_apply_on_savings_different_cardinalities(
                data.tour_2,
                data.tour_1,
                data.tour_1_section_nodes,
                subtour_2_index_slice,
                subtour_1_index_slice,
                data.calculate_savings,
                skip_savings
            )
        else:
            return data.apply_and_swap_on_savings(
                subtour_1_index_slice,
                subtour_2_index_slice,
                data.tour_2_section_nodes,
                data.tour_1_section_nodes,
            )

    @staticmethod
    def two_lambda_interchange(data: NeighborhoodData) -> tuple[Tour, Tour]:
        tour_1_edge_indices: tuple = data.tour_1_section_indices
        tour_2_edge_indices: tuple = data.tour_2_section_indices
        tour_1 = data.tour_1
        tour_2 = data.tour_2
        if len(tour_1_edge_indices + tour_2_edge_indices) != 4:
            raise ValueError('Subtour MUST only coincide with two nodes.')

        return data.apply_and_swap_on_savings(
            tour_1_edge_indices,
            tour_2_edge_indices,
            (tour_1[tour_1_edge_indices[0]], tour_2[tour_2_edge_indices[0]]),
            (tour_1[tour_1_edge_indices[1]], tour_2[tour_2_edge_indices[1]])
        )

    # INTRA-ROUTE-EXCHANGE
    @staticmethod
    def two_opt_move(
            tour: Tour,
            reference_vehicle: Vehicle,
            battery_threshold: float,
            savings_calc: Callable[[Tour, Tour, Vehicle, float], float | int],
            iterations: int = 5):
        altered_tour = Tour([])
        for _ in range(iterations):
            better_solution_found = False
            timeout = time.time() + 1
            while not better_solution_found and time.time() <= timeout:
                sub_tour_1, sub_tour_2 = NeighborhoodOperatorsImpl.get_random_tour_sections(tour, 2)
                indices_1, indices_2 = tour.get_indices_of(sub_tour_1), tour.get_indices_of(sub_tour_2)

                # swap nodes of sub_tour_1 (a1, b1) and sub_tour_2 (a2, b2)
                # so that they result in new_sub_1 (a1,a2) and new_sub_2 (b1, b2)
                new_sub_1, new_sub_2 = sub_tour_1.get_manual_copy(), sub_tour_2.get_manual_copy()
                if sum(indices_1) < sum(indices_2):
                    new_sub_1.slice_replace(slice(0, 2), (sub_tour_1[0], sub_tour_2[0]))
                    new_sub_2.slice_replace(slice(0, 2), (sub_tour_1[1], sub_tour_2[1]))
                else:
                    new_sub_1.slice_replace(slice(0, 2), (sub_tour_2[1], sub_tour_1[1]))
                    new_sub_2.slice_replace(slice(0, 2), (sub_tour_2[0], sub_tour_1[0]))

                altered_tour = tour.get_manual_copy()
                altered_tour.list_replace_with_tour(indices_1, new_sub_1)
                altered_tour.list_replace_with_tour(indices_2, new_sub_2)

                saving = savings_calc(tour, altered_tour, reference_vehicle, battery_threshold)
                if saving > 0:
                    better_solution_found = True
            if not better_solution_found:  # ==> ABORTED via time-out
                break
            tour = altered_tour
        return tour

    @staticmethod
    def get_random_tour_sections(tour: Tour, section_length: int) -> tuple[Tour, Tour]:
        get_random_node_index = lambda: random.randint(0, len(tour) - section_length)
        r = get_random_node_index()
        tour_1_section = Tour(tour[r:r + section_length])
        tour_2_section = tour_1_section.get_manual_copy()
        while tour_2_section == tour_1_section:
            r = get_random_node_index()
            tour_2_section = Tour(tour[r:r + section_length])
        return tour_1_section, tour_2_section

    @staticmethod
    def sequential_insertion(runner_client_nodes: list[Tour], tours: TourPlan | list[Tour], vehicle, battery_threshold):
        tours_copied = tours.get_manual_copy()

        for tour in tours_copied:
            if len(runner_client_nodes) == 0:
                return runner_client_nodes, tours_copied
            runner_to_node_tours: list[Tour] = []

            for node in tour[1:-1]:
                runner_to_node_tours = [
                    Tour([runner, node])
                    for runner
                    in runner_client_nodes
                ]
            runner_to_node_tours.sort(key=lambda x: x.get_costs_of_tour(vehicle, battery_threshold)[CostTypes.TOTAL])

            for runner_to_node in runner_to_node_tours:

                copied = tour.get_manual_copy()
                copied.nodes.insert(copied.nodes.index(runner_to_node[1]), runner_to_node[0])

                if all(ConstraintValidationStrategy(
                    constraint.value,
                    copied,
                    vehicle,
                    battery_threshold
                ).is_valid() for constraint in Constraints):
                    tours_copied[tour] = copied
                    tour = copied
                    runner_client_nodes.remove(runner_to_node[0])

        return runner_client_nodes, tours_copied

    @classmethod
    def get_random_tour_section(cls, tour, subtour_length):
        get_random_node_index = lambda: random.randint(1, len(tour) - subtour_length)
        r = get_random_node_index()
        tour_section = Tour(tour[r:r + subtour_length])
        return tour_section


class NeighborhoodOperators(Enum):
    TWO_OPT_MOVE = NeighborhoodOperatorsImpl.two_opt_move
    CROSS_EXCHANGE = NeighborhoodOperatorsImpl.cross_exchange
    TWO_LAMBDA_INTERCHANGE = NeighborhoodOperatorsImpl.two_lambda_interchange
    SEQUENTIAL_INSERTION = NeighborhoodOperatorsImpl.sequential_insertion

    def __call__(self, *args, **kwargs):
        self.value(*args, **kwargs)
