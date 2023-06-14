from collections import OrderedDict
from enum import Enum
from typing import Callable
import time
import random

from cevrp.constraints import Constraints, ConstraintValidationStrategy
from cevrp.cost_types import CostTypes
from cevrp.node import Node
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
    # RETURNS UN-PROCESSED OUTLIERS (list may be empty) AND MODIFIED TOURS
    def sequential_insertion(
            clients: list[Node],
            outliers: list[Node],
            tours: TourPlan | list[Tour],
            vehicle,
            battery_threshold
    ):
        tours_copied = tours.get_manual_copy()

        # ASSUME CLIENTS IS SUBSET OF OUTLIERS

        distances_outlier_to_depot: dict[[Node], float] = {}
        distances_non_outlier_to_depot: dict[[Node], float] = {}
        depot = Node.create_depot()

        # Calculate all distances to depot for every node and sort them in descending order.
        # Nodes are to be preferred which resemble outliers by putting them to the front of the distances-list.
        for outlier in outliers:
            distances_outlier_to_depot[outlier] = depot - outlier
        distances_outlier_to_depot_descending = OrderedDict(
            sorted(
                distances_outlier_to_depot.items(),
                key=lambda kv: kv[1],
                reverse=True
            ))

        for client in [c for c in clients if c != depot and c not in outliers]:
            distances_non_outlier_to_depot[client] = depot - client
        distances_non_outlier_to_depot_descending = OrderedDict(
            sorted(
                distances_non_outlier_to_depot.items(),
                key=lambda kv: kv[1],
                reverse=True
            ))

        distances_all_to_depot = distances_outlier_to_depot_descending | distances_non_outlier_to_depot_descending

        # Iterate over all clients, beginning from the furthest one away from the depot and
        # allocate it to any other tour.
        # Note that when allocating a client which is not an outlier to another tour,
        # that changes to the tour containing the client must be considered as well!
        for client in distances_all_to_depot.keys():
            client_allocated = False

            client_tour = None
            if client not in outliers:
                client_tour = [t for t in tours_copied if client in t][0]

            for tour in tours_copied:
                # As soon as a client had been allocated, stop the tour iteration
                # and process the next client.
                if client_allocated:
                    break

                # The current tour MUST NOT already contain client.
                if client in tour:
                    continue

                client_to_node_tours = [
                    Tour([client, tour_node])
                    for tour_node
                    in tour[1:-1]
                ]

                # Sorting by partial costs so that more efficient
                # routes will be preferred by getting processed sooner.
                client_to_node_tours.sort(
                    key=lambda x: x.get_costs_of_tour(vehicle, battery_threshold)[CostTypes.TOTAL])

                for client_to_node in client_to_node_tours:

                    copied = tour.get_manual_copy()
                    copied.nodes.insert(copied.nodes.index(client_to_node[1]), client_to_node[0])

                    # If current client is not an outlier (thus being part of a tour) then
                    # remove it from a tour's copy. If the tour is invalid, skip the current iteration.
                    client_tour_copied = None
                    if client_tour is not None:
                        client_tour_copied = client_tour.get_manual_copy()
                        client_tour_copied.remove(client_to_node[0])

                        if not all(ConstraintValidationStrategy(
                                constraint.value,
                                client_tour_copied,
                                vehicle,
                                battery_threshold
                        ).is_valid() for constraint in Constraints):
                            continue

                    # Apply all hypothetical changes to the actual tours.
                    if all(ConstraintValidationStrategy(
                            constraint.value,
                            copied,
                            vehicle,
                            battery_threshold
                    ).is_valid() for constraint in Constraints):
                        client_allocated = True
                        tours_copied[tour] = copied

                        if client_tour_copied is not None:
                            tours_copied[client_tour] = client_tour_copied
                            # If tour is empty (depot - depot) then delete
                            # from tour-collection.
                            if len(tours_copied[client_tour_copied]) <= 2:
                                tours_copied.tours.remove(client_tour_copied)

                        if client_to_node[0] in outliers:
                            outliers.remove(client_to_node[0])
                        break

        return outliers, tours_copied

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
