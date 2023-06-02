from typing import Self

from cevrp.node import Node
from cevrp.tour import Tour


class TourPlan:
    def __init__(self, tours: list[Tour]):
        self.tours = tours

    def __iter__(self):
        yield from self.tours

    def __len__(self):
        return len(self.tours)

    def __repr__(self):
        return " - ".join([str(t.id) for t in self])

    def __contains__(self, el):
        if isinstance(el, Tour):
            return el in self.tours
        if isinstance(el, list):
            return any(el == tour for tour in self.tours)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.tours[item]
        if isinstance(item, Tour):
            return self.tours[self.tours.index(item)]
        if isinstance(item, Node):
            return [tour for tour in self.tours if item in tour][0]

    def __setitem__(self, key, value):
        if isinstance(key, Tour) and isinstance(value, Tour):
            self.tours[self.tours.index(key)] = value

    def __isub__(self, other):
        if isinstance(other, Tour):
            self.tours = [tour for tour in self.tours if tour != other]
            return self
        if isinstance(other, list):
            if all(isinstance(el, Node) for el in other):
                self.tours = [tour for tour in self.tours if tour != other]
                return self

    def __iadd__(self, other):
        if isinstance(other, Tour):
            self.tours.append(other)
            return self
        if isinstance(other, list):
            if all(isinstance(el, Node) for el in other):
                self.tours.append(Tour(other))
                return self

    def __radd__(self, other):
        return other + self.tours

    def get_edges(self) -> dict[Tour, list[tuple[Node, Node]]]:
        return {tour: tour.get_edges() for tour in self.tours}

    def get_manual_copy(self) -> Self:
        return TourPlan([t.get_manual_copy() for t in self])
