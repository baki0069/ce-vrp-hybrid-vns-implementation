import logging
import logging
import random
import time

from numba import jit

from cevrp.cevrp_model import CEVRPVisualizer, CEVRPModel
from cevrp.constraints import Constraints, ConstraintValidationStrategy
from cevrp.cost_types import CostTypes
from cevrp.node import Node
from cevrp.savings_calculator import SavingsCalculator
from cevrp.tour import Tour
from cevrp.tour_plan import TourPlan
from cevrp.vnd.neighborhood_operators import NeighborhoodOperators, NeighborhoodData, \
    NeighborhoodOperatorsImpl

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

    previous_solutions = {}
    it = 0
    no_mutation = False

    if outliers is None:
        runner_clients = []
    else:
        runner_clients = outliers

    tours = [t for k, v in tourplan.items() if k != -1 for t in v.tours]
    t_total = time.time()
    while not no_mutation and it < 100:
        CEVRPVisualizer(model).visualize_tour_plan(TourPlan(tours))

        it += 1

        logging.info(f"BEGIN ITERATION {it}")
        logging.info(f"BEGIN TWO OPT MOVE ({it})")

        vehicle = model.vehicles[0]
        battery_threshold = model.battery_threshold
        local_optimum_found = False

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

        for i in range(len(tours)):
            for j in range(len(tours)):
                if i == j:
                    continue

                tour1 = tours[i]
                tour2 = tours[j]

                if len(tour1) == 3 and len(tour2) == 3:
                    continue

                for n in range(50):
                    old_costs = get_total_costs(tour1, tour2, vehicle, battery_threshold)
                    found_valid_subtours = False
                    s1 = Tour([])
                    s2 = Tour([])
                    t_cross_exchange = time.time()
                    while not found_valid_subtours and time.time() - t_cross_exchange < 2:
                        r1 = random.randint(1, len(tour1)-2)
                        r2 = random.randint(1, len(tour2)-2)
                        s1 = NeighborhoodOperatorsImpl.get_random_subtour(tour1, r1)
                        s2 = NeighborhoodOperatorsImpl.get_random_subtour(tour2, r2)
                        if (s1.nodes.count(Node.create_depot()) == 0 and s2.nodes.count(Node.create_depot()) == 0) \
                                and not (len(s1) == 1 and len(s2) == 1):
                            found_valid_subtours = True

                    if not found_valid_subtours:
                        logging.critical(f"Could not find valid subtours for {tour1} and {tour2}")
                        break

                    data = NeighborhoodData(
                        tour1,
                        tour2,
                        s1.nodes,
                        s2.nodes,
                        vehicle,
                        battery_threshold,
                        SavingsCalculator.get_savings
                    )

                    tour1_candidate, tour2_candidate = shaker.CROSS_EXCHANGE(data)

                    if is_invalid(tour1_candidate, vehicle, battery_threshold) or is_invalid(tour2_candidate, vehicle, battery_threshold):
                        continue

                    new_costs = get_total_costs(tour1_candidate, tour2_candidate, vehicle, battery_threshold)
                    if new_costs < old_costs:
                        local_optimum_found = True
                        logging.info("LOCAL OPTIMUM FOUND VIA CROSS EXCHANGE")
                        tour1 = tour1_candidate
                        tour2 = tour2_candidate
                        tours[i] = tour1_candidate
                        tours[j] = tour2_candidate

        if local_optimum_found:
            continue
        else:
            logging.warning(f"NO LOCAL OPTIMUM VIA CROSS EXCHANGE AT ({it})")

        logging.info(f"BEGIN TWO LAMBDA INTERCHANGE ({it})")

        for i in range(len(tours)):
            for j in range(len(tours)):
                if i == j:
                    continue

                tour1 = tours[i]
                tour2 = tours[j]

                edges = [(e1, e2) for e1 in tour1.get_edges() for e2 in tour2.get_edges()]

                for k in range(100):
                    old_costs = get_total_costs(tour1, tour2, vehicle, battery_threshold)

                    r = random.randint(0, len(edges) - 1)

                    edge1, edge2 = edges[r]
                    if edge1.count(Node.create_depot()) == 1 or edge2.count(Node.create_depot()) == 1:
                        continue

                    data = NeighborhoodData(
                        tour1,
                        tour2,
                        edge1,
                        edge2,
                        vehicle,
                        battery_threshold,
                        SavingsCalculator.get_savings
                    )
                    tour1_candidate, tour2_candidate = shaker.TWO_LAMBDA_INTERCHANGE(data)

                    if is_invalid(tour1_candidate, vehicle, battery_threshold) or is_invalid(tour2_candidate, vehicle, battery_threshold):
                        continue

                    new_costs = get_total_costs(tour1_candidate, tour2_candidate, vehicle, battery_threshold)
                    if new_costs < old_costs:
                        local_optimum_found = True
                        logging.info("LOCAL OPTIMUM FOUND VIA TWO LAMBDA INTERCHANGE")
                        tour1, tour2 = tour1_candidate, tour2_candidate
                        tours[i] = tour1
                        tours[j] = tour2
                        edges = [(e1, e2) for e1 in tour1.get_edges() for e2 in tour2.get_edges()]

        if local_optimum_found:
            continue
        else:
            logging.warning(f"NO LOCAL OPTIMUM VIA TWO LAMBDA INTERCHANGE AT ({it})")

        logging.critical(f"END OF LOOP {it} -> {round(time.time() - t_total, 2)} seconds")

        previous_solutions[it] = round(get_total_costs2(tours, vehicle, battery_threshold), 2)
        if it >= 5 and len(set([v for k, v in previous_solutions.items() if k > it-3])) == 1:
            no_mutation = True

    CEVRPVisualizer(model).visualize_tour_plan(TourPlan(tours))
    print("END")
