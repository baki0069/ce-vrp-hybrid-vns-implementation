from cevrp.cost_types import CostTypes
from cevrp.tour import Tour
from cevrp.vehicle import Vehicle
from cevrp.node import Node


class SavingsCalculator:
    @staticmethod
    def get_battery_recharging_cost(distance, vehicle: Vehicle):
        return (distance * vehicle.battery.consumption_rate) / vehicle.battery.charging_rate

    @staticmethod
    def calculate_savings(i: Node, j: Node, vehicle: Vehicle):
        node_i = i
        node_j = j
        depot = Node.create_depot()
        distance_i0 = node_i - depot
        distance_0j = depot - node_j
        distance_ij = node_i - node_j

        calculate_recharging_cost = SavingsCalculator.get_battery_recharging_cost
        battery_recharging_cost_i0 = calculate_recharging_cost(distance_i0, vehicle)
        battery_recharging_cost_0j = calculate_recharging_cost(distance_0j, vehicle)
        battery_recharging_cost_ij = calculate_recharging_cost(distance_ij, vehicle)

        cost_i0 = distance_i0 + battery_recharging_cost_i0 + node_i.service_time
        cost_0j = distance_0j + battery_recharging_cost_0j + node_j.service_time
        cost_ij = distance_ij + battery_recharging_cost_ij + node_i.service_time + node_j.service_time

        savings = cost_i0 + cost_0j - cost_ij
        return savings

    @staticmethod
    def get_savings(old_tour: Tour, new_tour: Tour, vehicle: Vehicle, battery_threshold: float) -> float | int:
        old = old_tour.get_costs_of_tour(vehicle, battery_threshold)[CostTypes.TOTAL]
        new = new_tour.get_costs_of_tour(vehicle, battery_threshold)[CostTypes.TOTAL]
        return old - new
