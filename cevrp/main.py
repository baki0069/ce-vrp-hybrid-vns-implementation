import cProfile
import pstats
import random
import timeit

from cevrp.cevrp_model import CEVRPModel, CEVRPVisualizer
from cevrp.tour import Tour
from cevrp.vnd import cevrp_optimizer
from cevrp.vehicle import *


# node information:
#   - demand
# vehicle information:
#   - distance travelled per unit of time
#   - delivery capacity
#   - total distance
#   - battery information:
#       + MUST BE FULLY RECHARGED EACH TIME WHEN EXITING A CUSTOMER LOCATION
#       - charge capacity (EQUAL TO CHARGE NEEDED FOR THE LONGEST DISTANCE BETWEEN TWO NODES)
#       - speed of recharge per unit of time
#       - speed of discharge per unit of time
# total cost comprised of:
#   - distance travelled
#   - time spent recharging battery

def generate_data_set(
        num_customers,
        num_vehicles,
        max_demand,
        max_service_time,
        max_distance,
        commodity_capacity,
        max_battery_capacity,
        battery_consumption_rate,
        charging_rate,
):
    nodes = []
    vehicles = []

    depot = Node.create_depot()
    nodes.append(depot)

    # Create customers
    demands = [random.randint(1, max_demand) for _ in range(num_customers)]
    service_times = [random.randint(1, max_service_time) for _ in range(num_customers)]
    x_y = [(random.randint(-100, 100), random.randint(-100, 100)) for _ in range(num_customers)]
    nodes.extend(Node.list_create(x_y, demands, service_times))

    # Create vehicles
    for i in range(1, num_vehicles + 1):
        vehicle = Vehicle(i, commodity_capacity, max_battery_capacity, battery_consumption_rate, charging_rate,
                          max_distance)
        vehicles.append(vehicle)

    return CEVRPModel(nodes, vehicles)


# Example usage
num_customers = 100
num_vehicles = 10
max_demand = 10
max_distance = 300
max_service_time = 10
max_capacity = 100
max_battery_capacity = 3000
max_battery_consumption = 10
max_charging_rate = 10

data = generate_data_set(
    num_customers,
    num_vehicles,
    max_demand,
    max_service_time,
    max_distance,
    max_capacity,
    max_battery_capacity,
    max_battery_consumption,
    max_charging_rate,
)
clustered_tour_plans = {}
data.cluster_nodes(27, 5)
visualizer = CEVRPVisualizer(data)
visualizer.visualize_clusters()
for cluster_key in data.node_clusters.keys():
    if cluster_key == -1:
        continue
    clustered_tour_plans[cluster_key] = data.generate_cws_solution(data.node_clusters[cluster_key])


#
# edges_per_tour = []
# for _, tour_plan in clustered_tour_plans.items():
#     visualizer.visualize_tour_plan(tour_plan)
#     edges_per_tour.append(tour_plan.get_edges())
#


for i in range(10, 100, 10):
    cProfile.run(f"""
cevrp_optimizer.optimize_tours(
    clustered_tour_plans,
    data,
    data.node_clusters[-1] if -1 in data.node_clusters.keys() else None,
    {i}
)""", f'restats_{i}')

    p = pstats.Stats(f'restats_{i}')
    p.strip_dirs().sort_stats(pstats.SortKey.TIME).print_stats()

# def test_costs_of_tour():
#     nodes = Node.list_create(
#         [(1, 1), (2, 1), (3, 1), (5, 10), (-3, -5), (5, 8)],
#         [1, 2, 4, 5, 6, 7],
#         [4, 5, 4, 5, 4, 5]
#     )
#     veh = Vehicle(1, 1, 3000, 10, 10, 4000)
#     tour = Tour(nodes)
#     for n in range(100000):
#         cevrp_optimizer.is_invalid(tour, veh, 1)
#         # tour.get_costs_of_tour(veh, 5000)


# cProfile.run("""test_costs_of_tour()""")
