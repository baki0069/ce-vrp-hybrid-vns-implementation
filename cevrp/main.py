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


# def init(num_customers):
num_customers = 5
num_vehicles = 5
max_demand = 10
max_distance = 400
max_service_time = 10
max_capacity = 250
max_battery_capacity = 800
max_battery_consumption = 10
max_charging_rate = 2

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
data.cluster_nodes(40, 2)
visualizer = CEVRPVisualizer(data)
visualizer.visualize_clusters()
for cluster_key in data.node_clusters.keys():
    if cluster_key == -1:
        continue
    clustered_tour_plans[cluster_key] = data.generate_cws_solution(data.node_clusters[cluster_key])

cevrp_optimizer.optimize_tours(
    clustered_tour_plans,
    data,
    data.node_clusters[-1] if -1 in data.node_clusters.keys() else None
)


# for i in range(10, 20, 2):
    # cProfile.run(f"""
    # init(i)
# """, f'performance_analysis_{i}_customers')
    # p = pstats.Stats(f'performance_analysis_{i}_customers')
    # p.strip_dirs().sort_stats(pstats.SortKey.TIME).print_stats()

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


