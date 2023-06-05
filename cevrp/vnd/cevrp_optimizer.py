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


def optimize_tours(tourplan: dict[[any], TourPlan], model: CEVRPModel, outliers, max_interchange_iterations):
    logging.getLogger().setLevel(logging.INFO)

    all_tour_plans = []

    previous_solutions = {}
    it = 0
    no_mutation = False

    if outliers is None:
        runner_clients = []
    else:
        runner_clients = outliers

    tours = [t for k, v in tourplan.items() if k != -1 for t in v.tours]
    vehicle = model.vehicles[0]
    battery_threshold = model.battery_threshold
    t_total = time.time()
    while not no_mutation and it < 100:
        it += 1

        logging.info(f"BEGIN ITERATION {it}")
        logging.info(f"BEGIN TWO OPT MOVE ({it})")

        local_optimum_found = False

        all_tour_plans.append((TourPlan([t.get_manual_copy() for t in tours]), it))

        for j in range(len(tours)):
            tour2 = tours[j]
            old_costs = get_total_costs2([tour2], vehicle, battery_threshold)

            tour2_candidate = shaker.TWO_OPT_MOVE(
                tour2,
                vehicle,
                battery_threshold,
                SavingsCalculator.get_savings,
                100
            )
            new_costs = get_total_costs2([tour2_candidate], vehicle, battery_threshold)

            if is_invalid(tour2_candidate, vehicle, battery_threshold):
                continue

            if new_costs < old_costs:
                local_optimum_found = True
                logging.info("LOCAL OPTIMUM FOUND VIA TWO OPT MOVE")
                tours[j] = tour2_candidate

        if local_optimum_found:
            local_optimum_found = False
        else:
            logging.warning(f"NO LOCAL OPTIMUM VIA TWO OPT MOVE AT ({it})")

        if len(runner_clients) != 0:
            logging.info(f"BEGIN SEQUENTIAL INSERTION ({it})")

            # SEQUENTIAL INSERTION INCLUDES CHECKS FOR TOUR VALIDATION
            copied_runner_clients = [rc for rc in runner_clients]
            runner_clients, tp = NeighborhoodOperators.SEQUENTIAL_INSERTION(
                copied_runner_clients,
                TourPlan(tours),
                vehicle,
                battery_threshold
            )

            tours = tp.tours
            logging.info(f"END SEQUENTIAL INSERTION ({it})")

        logging.info(f"BEGIN CROSS EXCHANGE ({it})")

        for n in range(max_interchange_iterations):
            for i in range(len(tours)):
                for j in range(len(tours)):
                    if i == j:
                        continue

                    tour1 = tours[i]
                    tour2 = tours[j]

                    if len(tour1) == 3 and len(tour2) == 3:
                        continue

                    old_costs = get_total_costs(tour1, tour2, vehicle, battery_threshold)
                    found_valid_subtours = False
                    s1 = Tour([])
                    s2 = Tour([])
                    t_cross_exchange = time.time()
                    while not found_valid_subtours and time.time() - t_cross_exchange < 2:
                        r1 = random.randint(1, len(tour1)-2)
                        r2 = random.randint(1, len(tour2)-2)
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

                    if is_invalid(tour1_candidate, vehicle, battery_threshold) or is_invalid(tour2_candidate, vehicle, battery_threshold):
                        continue

                    new_costs = get_total_costs(tour1_candidate, tour2_candidate, vehicle, battery_threshold)
                    if new_costs < old_costs:
                        local_optimum_found = True
                        logging.info("LOCAL OPTIMUM FOUND VIA CROSS EXCHANGE")
                        tours[i] = tour1_candidate
                        tours[j] = tour2_candidate

        if local_optimum_found:
            continue
        else:
            logging.warning(f"NO LOCAL OPTIMUM VIA CROSS EXCHANGE AT ({it})")

        logging.info(f"BEGIN TWO LAMBDA INTERCHANGE ({it})")

        for n in range(max_interchange_iterations):
            for i in range(len(tours)):
                for j in range(len(tours)):
                    if i == j:
                        continue

                    tour1 = tours[i]
                    tour2 = tours[j]

                    edges = [(e1, e2) for e1 in tour1.get_edges() for e2 in tour2.get_edges()]

                    old_costs = get_total_costs(tour1, tour2, vehicle, battery_threshold)

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

                    if is_invalid(tour1_candidate, vehicle, battery_threshold) or is_invalid(tour2_candidate, vehicle, battery_threshold):
                        continue

                    new_costs = get_total_costs(tour1_candidate, tour2_candidate, vehicle, battery_threshold)
                    if new_costs < old_costs:
                        local_optimum_found = True
                        logging.info("LOCAL OPTIMUM FOUND VIA TWO LAMBDA INTERCHANGE")
                        tours[i] = tour1
                        tours[j] = tour2
                        # edges = [(e1, e2) for e1 in tour1.get_edges() for e2 in tour2.get_edges()]

        if local_optimum_found:
            continue
        else:
            logging.warning(f"NO LOCAL OPTIMUM VIA TWO LAMBDA INTERCHANGE AT ({it})")

        logging.critical(f"END OF LOOP {it} -> {round(time.time() - t_total, 2)} seconds")

        previous_solutions[it] = round(get_total_costs2(tours, vehicle, battery_threshold), 2)
        if it >= 5 and len(set([v for k, v in previous_solutions.items() if k > it-3])) == 1:
            no_mutation = True

    CEVRPVisualizer(model).visualize_tour_plan(TourPlan(tours))
    show_costs_progression(all_tour_plans, vehicle, battery_threshold, model)
    print("END")


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
