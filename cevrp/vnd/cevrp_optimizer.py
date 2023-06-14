import logging
import logging
import random
import time

import matplotlib.pyplot as plt
import numpy as np
from numba import jit

from cevrp.cevrp_model import CEVRPVisualizer, CEVRPModel
from cevrp.constraints import Constraints, ConstraintValidationStrategy
from cevrp.cost_types import CostTypes
from cevrp.node import Node
from cevrp.savings_calculator import SavingsCalculator
from cevrp.tour import Tour
from cevrp.tour_plan import TourPlan
from cevrp.vnd.neighborhood_operators import NeighborhoodOperators, NeighborhoodOperatorsImpl
from cevrp.vnd.neighborhood_data import NeighborhoodData

shaker = NeighborhoodOperators


def get_total_costs(tour1, tour2, vehicle, battery_threshold):
    return tour1.get_costs_of_tour(+vehicle, battery_threshold)[CostTypes.TOTAL] \
        + tour2.get_costs_of_tour(+vehicle, battery_threshold)[CostTypes.TOTAL]


def get_total_costs2(tours, vehicle, battery_threshold):
    return sum(t.get_costs_of_tour(+vehicle, battery_threshold)[CostTypes.TOTAL] for t in tours)


def is_invalid(tour, vehicle, battery_threshold):
    return not all(ConstraintValidationStrategy(
                    constraint.value,
                    tour,
                    vehicle,
                    battery_threshold,
            ).is_valid() for constraint in Constraints)


def optimize_tours(tourplan: dict[[any], TourPlan], model: CEVRPModel, outliers):
    logging.getLogger().setLevel(logging.INFO)

    all_tour_plans = []

    previous_solutions = {}
    it = 0
    no_mutation = False

    num_vehicles = len(model.vehicles)

    # runner clients represent client nodes which were detected as outliers
    # via DBSCAN
    if outliers is None:
        runner_clients: list[Node] = []
    else:
        runner_clients: list[Node] = outliers

    # normalize lists of tours in clustered tour-plans into flat list of all tours
    # for all clusters which do not contain outliers <=> for all cluster_key != -1
    tours = [tour for cluster_key, tour_plan in tourplan.items() if cluster_key != -1 for tour in tour_plan.tours]

    # reference vehicle for tour cost computations
    vehicle = model.vehicles[0]
    battery_threshold = model.battery_threshold
    t_total = time.time()
    has_completely_iterated = False

    n_s = 1

    while n_s < 6:
        CEVRPVisualizer(model).visualize_tour_plan(TourPlan(tours))

        it += 1

        logging.info(f"BEGIN ITERATION {it}")

        # Variable Neighborhood Search will apply the same Neighborhood Operator
        # as long as a local optimum has been found. In the case that no further local optimum
        # has been found by applying an operator, the next operator is applied to the set of
        # tours found so far. For each local optimum found, the neighborhood structure to be
        # applied resets to the first neighborhood operator.
        # As soon as for a defined number of successive iterations all neighborhood structures
        # could not find a local optimum, the tour plan will be returned.

        if len(tours) != 0:
            all_tour_plans.append((TourPlan([t.get_manual_copy() for t in tours]), it))

        # Each neighborhood operator to be applied is applied multiple times to each tour
        # or pair of tours. Only those tour changes are saved (here: the original tour*s
        # overwritten), if they represent a better, i.e. more cost-efficient alternative,
        # while respecting the capacitive constraints and those associated with the use
        # of electric vehicles.

        tours_prime = [t.get_manual_copy() for t in tours]

        match n_s:
            case 1:
                print("two opt move")
                two_opt_move(tours_prime, battery_threshold, vehicle)
                print("end")
            case 2:
                print("cross exchange")
                cross_exchange(tours_prime, battery_threshold, vehicle)
                print("end")
            case 3:
                print("two lambda interchange")
                two_lambda_interchange(tours, battery_threshold, vehicle)
                print("end")
            case 4:
                print("sequential insertion")
                runner_clients, tp = NeighborhoodOperators.SEQUENTIAL_INSERTION(
                    model.nodes,
                    runner_clients,
                    TourPlan(tours_prime),
                    vehicle,
                    battery_threshold
                )
                print("end")
                tours_prime = tp.tours

                # adding all outliers if there are still any
                if it >= 5 and len(runner_clients) != 0:
                    for runner in runner_clients:
                        tours_prime.append(Tour([Node.create_depot(), runner, Node.create_depot()]))
                        runner_clients.remove(runner)

        # variable neighborhood descent
        n_k = 1
        tours_prime_processed = [t.get_manual_copy() for t in tours_prime]
        while n_k <= 2:
            match n_k:
                case 1:
                    print("two opt move")
                    two_opt_move(tours_prime_processed, battery_threshold, vehicle)
                    print("end")
                case 2:
                    print("cross exchange")
                    cross_exchange(tours_prime, battery_threshold, vehicle)
                    print("end")
            if get_total_costs2(
                    tours_prime_processed,
                    vehicle,
                    battery_threshold
            ) < get_total_costs2(tours_prime, vehicle, battery_threshold):
                tours_prime = [t.get_manual_copy() for t in tours_prime_processed]
                n_k = 1
            else:
                n_k += 1

        # move or not
        if len(set(n for t in tours for n in t)) < len(set(n for t in tours_prime for n in t)) \
            or get_total_costs2(
                tours_prime,
                vehicle,
                battery_threshold
        ) < get_total_costs2(tours, vehicle, battery_threshold):
            tours = [t.get_manual_copy() for t in tours_prime]
            n_s = 1
        else:
            n_s += 1

        logging.critical(f"END OF LOOP {it} -> {round(time.time() - t_total, 2)} seconds")

        previous_solutions[it] = round(get_total_costs2(tours, vehicle, battery_threshold), 2)
        if len(runner_clients) == 0 and it >= 10 and len(set([v for k, v in previous_solutions.items() if k > it-6])) == 1:
            break

    CEVRPVisualizer(model).visualize_tour_plan(TourPlan(tours))
    show_costs_progression(all_tour_plans, vehicle, battery_threshold, model)
    for tour in tours:
        print(tour)
    print("END")


def two_lambda_interchange(tours, battery_threshold, vehicle):
    for i in range(len(tours)):
        for j in range(len(tours)):
            for n in range(20):
                if i == j:
                    continue

                tour1 = tours[i].get_manual_copy()
                tour2 = tours[j].get_manual_copy()

                edges = [(e1, e2) for e1 in tour1.get_edges() for e2 in tour2.get_edges()]

                r = random.randint(0, len(edges) - 1)

                edge1, edge2 = edges[r]
                if edge1.count(Node.create_depot()) == 1 or edge2.count(Node.create_depot()) == 1:
                    continue

                data = NeighborhoodData(
                    tour1,
                    tour2,
                    vehicle,
                    battery_threshold,
                    SavingsCalculator.get_savings,
                    tour_1_section_indices=[tour1.nodes.index(n) for n in tour1 if n in edge1],
                    tour_2_section_indices=[tour2.nodes.index(n) for n in tour2 if n in edge2],
                )
                tour1_candidate, tour2_candidate = shaker.TWO_LAMBDA_INTERCHANGE(data)

                if is_invalid(
                        tour1_candidate,
                        vehicle,
                        battery_threshold
                ) or is_invalid(
                    tour2_candidate,
                    vehicle,
                    battery_threshold
                ):
                    continue

                tours[i] = tour1
                tours[j] = tour2


def cross_exchange(tours, battery_threshold, vehicle):
    for i in range(len(tours)):
        for j in range(len(tours)):
            for n in range(20):
                if i == j:
                    continue

                tour1 = tours[i].get_manual_copy()
                tour2 = tours[j].get_manual_copy()

                if len(tour1) == 3 and len(tour2) == 3:
                    continue

                found_valid_subtours = False
                s1 = Tour([])
                s2 = Tour([])
                t_cross_exchange = time.time()
                while not found_valid_subtours and time.time() - t_cross_exchange < 2:
                    r1 = random.randint(1, len(tour1) - 2)
                    r2 = random.randint(1, len(tour2) - 2)
                    s1 = NeighborhoodOperatorsImpl.get_random_tour_section(tour1, r1)
                    s2 = NeighborhoodOperatorsImpl.get_random_tour_section(tour2, r2)
                    if (s1.nodes.count(Node.create_depot()) == 0 and s2.nodes.count(Node.create_depot()) == 0) \
                            and not (len(s1) == 1 and len(s2) == 1):
                        found_valid_subtours = True

                if not found_valid_subtours:
                    logging.critical(f"Could not find valid subtours for {tour1} and {tour2}")
                    break

                data = NeighborhoodData(
                    tour1,
                    tour2,
                    vehicle,
                    battery_threshold,
                    SavingsCalculator.get_savings,
                    tour_1_section_nodes=s1.nodes,
                    tour_2_section_nodes=s2.nodes,
                )

                tour1_candidate, tour2_candidate = shaker.CROSS_EXCHANGE(data)

                if is_invalid(
                        tour1_candidate,
                        vehicle,
                        battery_threshold
                ) or is_invalid(
                    tour2_candidate,
                    vehicle,
                    battery_threshold
                ):
                    continue

                tours[i] = tour1_candidate
                tours[j] = tour2_candidate


def two_opt_move(tours, battery_threshold, vehicle):
    for j in range(len(tours)):
        tour2 = tours[j].get_manual_copy()

        tour2_candidate = shaker.TWO_OPT_MOVE(
            tour2,
            vehicle,
            battery_threshold,
            SavingsCalculator.get_savings,
            100
        )

        if is_invalid(tour2_candidate, vehicle, battery_threshold):
            continue

        tours[j] = tour2_candidate


def show_costs_progression(tourplans_per_iteration: list[tuple[TourPlan, int]], vehicle, battery_threshold, model):
    avg_costs = []
    visited_ratio = []
    for tp, i in tourplans_per_iteration:
        avg_costs_per_tour = sum(t.get_costs_of_tour(vehicle, battery_threshold)[CostTypes.TOTAL] for t in tp) / len(tp)
        avg_costs.append(avg_costs_per_tour)

        visited_nodes = set(n for t in tp for n in t)
        ratio = len(visited_nodes) / len(model.nodes)
        visited_ratio.append(ratio * 100)

    tour_indices = range(1, len(avg_costs) + 1)

    fig, ax1 = plt.subplots()

    ax1.plot(tour_indices, avg_costs, marker='o', color='blue')
    ax1.set_xlabel('Tour')
    ax1.set_ylabel('Cost', color='blue')
    ax1.tick_params('y', colors='blue')

    ax2 = ax1.twinx()
    ax2.plot(tour_indices, visited_ratio, marker='o', color='green')
    ax2.set_ylabel('Visited Ratio (%)', color='green')
    ax2.tick_params('y', colors='green')

    plt.title('Tour Costs and Visited Ratio')
    plt.xticks(tour_indices)
    plt.grid(True)
    plt.show()
