import random

import numpy as np
from matplotlib import pyplot as plt
from sklearn.cluster import DBSCAN

from cevrp.constraints import *
from cevrp.savings_calculator import SavingsCalculator
from cevrp.cost_types import CostTypes
from cevrp.tour_plan import TourPlan
from cevrp.tour import Tour
from cevrp.vehicle import *


class CEVRPModel:
    def __init__(self, nodes: list[Node], vehicles: list[Vehicle]):
        depot = Node.create_depot()
        if depot not in nodes:
            nodes.insert(0, depot)
        self.nodes = nodes
        self.vehicles = vehicles
        self.battery_threshold = self.calculate_battery_threshold()
        self.node_clusters = {}

    def get_node_by_id(self, id: int):
        nodes = [node for node in self.nodes if node.node_id == id]
        if len(nodes) == 0:
            raise ValueError('NODE-ID NON-EXISTENT')
        else:
            return nodes[0]

    def add_node(self, node: Node):
        self.nodes.append(node)

    def add_vehicle(self, vehicle: Vehicle):
        self.vehicles.append(vehicle)

    def calculate_battery_threshold(self):
        max_distance = 0
        for i in range(1, len(self.nodes)):
            for j in range(i + 1, len(self.nodes)):
                distance = self.nodes[i] - self.nodes[j]
                # distance = self.calculate_distance(self.nodes[i], self.nodes[j])
                if distance > max_distance:
                    max_distance = distance

        return max_distance * self.vehicles[0].battery.consumption_rate

    def cluster_nodes(self, eps, min_samples):
        coordinates = np.array([(node.x, node.y) for node in self.nodes if (node.x, node.y) != (0, 0)])
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coordinates)
        labels = clustering.labels_

        # Create clusters dictionary
        clusters = {}
        for node, label in zip([node for node in self.nodes if (node.x, node.y) != (0, 0)], labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(node)

        self.node_clusters = clusters

    def generate_cws_solution(self, nodes=None) -> TourPlan:
        # Step 1: Construct n tours: v0 → vi → v0
        depot = Node.create_depot()
        if nodes is None:
            tour_plan = TourPlan([Tour([depot, node, depot]) for node in self.nodes])
        else:
            tour_plan = TourPlan([Tour([depot, node, depot]) for node in nodes])
        if [depot, depot, depot] in tour_plan:
            # remove trivial tour from tour_plan
            tour_plan -= [depot, depot, depot]

        # Calculate savings
        no_additional_savings_exist = False

        savings = []
        savings_calc = SavingsCalculator().calculate_savings
        reference_vehicle = self.vehicles[0]
        while not no_additional_savings_exist:
            last_savings = savings
            savings = []
            for tour1 in tour_plan:
                for tour2 in [t for t in tour_plan if t != tour1]:
                    savings.append((savings_calc(tour1[1], tour2[1], reference_vehicle), tour1[1], tour2[1]))
                    if len(tour1) > 3:
                        savings.append((savings_calc(tour1[-2], tour2[1], reference_vehicle), tour1[-2], tour2[1]))
                    if len(tour2) > 3:
                        savings.append((savings_calc(tour1[1], tour2[-2], reference_vehicle), tour1[1], tour2[-2]))
                    if len(tour1) > 3 and len(tour2) > 3:
                        savings.append((savings_calc(tour1[-2], tour2[-2], reference_vehicle), tour1[-2], tour2[-2]))
            savings = list(set(savings))
            savings.sort(reverse=True)

            if last_savings == savings:
                no_additional_savings_exist = True
                continue

            # Merge tours based on savings
            for saving, i, j in savings:
                merged = False

                # Check constraints for merging tours
                tour_containing_i = tour_plan[i]
                tour_containing_j = tour_plan[j]
                if self.check_merge_constraints(tour_containing_i, tour_containing_j):
                    # Merge tours
                    merged_tour = tour_containing_i + tour_containing_j
                    tour_plan -= tour_containing_i
                    tour_plan -= tour_containing_j
                    tour_plan += merged_tour
                    merged = True

                if merged:
                    break

        return tour_plan

    def check_merge_constraints(self, tour1: Tour, tour2: Tour):
        # Check capacity constraint
        merged = tour1 + tour2

        return all(ConstraintValidationStrategy(
                constraint.value,
                merged,
                self.vehicles[0],
                self.battery_threshold
            ).is_valid() for constraint in Constraints)


class CEVRPVisualizer:
    def __init__(self, model: CEVRPModel):
        self.model = model

    def visualize_clusters(self):
        node_clusters = self.model.node_clusters
        nodes = self.model.nodes

        # Create a list of colors for each cluster
        colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k']

        # Plot the nodes
        for node in nodes:
            plt.scatter(node.x, node.y, color='black')
            plt.text(node.x, node.y, str(node.node_id), fontsize=8, ha='center', va='bottom')

        # Plot the clusters
        for cluster_id, nodes in node_clusters.items():
            color = colors[cluster_id % len(colors)]
            for node in nodes:
                plt.scatter(node.x, node.y, color=color)

        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Clustered Nodes')
        plt.show()

    def visualize_tour_plan(self, tour_plan: TourPlan):
        model = self.model

        # Plot the nodes
        for node in model.nodes:
            plt.scatter(node.x, node.y, color='black')

        reference_vehicle = model.vehicles[0]

        # Plot the tour
        for tour in [t for t in tour_plan if len(t) > 1]:
            color = (
                random.uniform(0, 1),
                random.uniform(0, 1),
                random.uniform(0, 1),
            )

            annotated = False
            for node in tour:
                node1 = model.get_node_by_id(node.node_id)
                node2 = model.get_node_by_id(tour.get_next_node(node).node_id)
                # plt.plot([node1.x, node2.x], [node1.y, node2.y], color=color)
                plt.arrow(node1.x, node1.y, node2.x - node1.x, node2.y - node1.y, color=color,
                          length_includes_head=True, head_width=0.4, head_length=0.6)
                if not annotated:
                    reference_vehicle = +reference_vehicle
                    costs = tour.get_costs_of_tour(reference_vehicle, model.battery_threshold)
                    plt.text(node2.x + 1.5, node2.y + 1.5,
                             f"{CostTypes.TOTAL.printable}: {round(costs[CostTypes.TOTAL], 1)}")
                    plt.text(node2.x + 1.5, node2.y + 11.5,
                             f"{CostTypes.DISTANCE.printable}: {round(costs[CostTypes.DISTANCE], 1)}")
                    plt.text(node2.x + 1.5, node2.y + 21.5,
                             f"{CostTypes.BATTERY_RECHARGING.printable}: {round(costs[CostTypes.BATTERY_RECHARGING], 1)}")
                    plt.text(node2.x + 1.5, node2.y + 31.5,
                             f"{CostTypes.DEMAND.printable}: {round(costs[CostTypes.DEMAND], 1)}")
                    annotated = True

            # Connect the last node to the first node to complete the tour
            first_node = tour[0]
            last_node = tour[-1]
            plt.plot([last_node.x, first_node.x], [last_node.y, first_node.y], color=color)

        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Tour Visualization')
        plt.show()
