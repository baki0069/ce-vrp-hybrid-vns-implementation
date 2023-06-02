from enum import Enum


class CostTypes(Enum):
    SERVICE_TIME = 'srv'
    TOTAL = 'tot',
    DISTANCE = 'dis',
    BATTERY_RECHARGING = 'brc',
    DEMAND = 'dmd',

    def __init__(self, printable: str):
        self.printable = printable
