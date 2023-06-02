from dataclasses import dataclass
from typing import Self

from cevrp.node import Node


@dataclass
class VehicleBatteryData:
    capacity: float
    consumption_rate: float
    charging_rate: float


class Vehicle:
    def __init__(
            self,
            vehicle_id,
            commodity_capacity,
            battery_capacity,
            battery_consumption_rate,
            charging_rate,
            distance_threshold,
    ):
        self.vehicle_id = vehicle_id
        self.distance_threshold = distance_threshold
        self.commodity_capacity = commodity_capacity
        self.battery = VehicleBatteryData(
            battery_capacity,
            battery_consumption_rate,
            charging_rate,
        )
        self.current_battery_level = self.battery.capacity

    # diminishes battery charge by amount necessary to cover distance between two nodes if
    # other-operand is of type (node, node).
    def __sub__(self, other: tuple[Node, Node]) -> Self:
        self.current_battery_level -= (other[0]-other[1]) * self.battery.consumption_rate
        return self

    # recharges battery
    def __pos__(self) -> Self:
        self.current_battery_level = self.battery.capacity
        return self

    def __invert__(self) -> float:
        return self.battery.capacity - self.current_battery_level
