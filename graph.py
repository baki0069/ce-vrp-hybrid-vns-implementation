from copy import copy
from typing import Optional


class Node:
    def __init__(self, element):
        self.element = element
        self.degree = 0

    def is_source(self) -> bool:
        return self.degree == 1


class Edge:
    def __init__(self, nodes: tuple[Node, Node], cost: Optional[float] = None):
        self.nodes = nodes
        a, b = self.nodes
        a.degree += 1
        b.degree += 1
        self.cost = cost

    def __str__(self):
        a, b = self.nodes
        return f"({a.element}|D:{a.degree}) -{self.cost}- ({b.element}|D:{b.degree})"


class GraphComponentsBuilder:
    def __init__(self):
        self.current_node_index = 0
        self.node = Node(str(self.current_node_index))

    def generate_node(self) -> Node:
        current_node = copy(self.node)
        self.current_node_index += 1
        self.node = Node(str(self.current_node_index))
        return current_node

    def build_node(self) -> Node:
        return self.generate_node()

    def build_edge(self, cost: Optional[float] = None) -> Edge:
        return Edge((self.generate_node(), self.generate_node()), cost)


class Graph:
    def __init__(self, edges: set[Edge]):
        self.edges = edges
        self.reset_degrees()

        self.nodes = set()
        for edge in edges:
            a, b = edge.nodes
            self.nodes.add(a)
            self.nodes.add(b)

        if self.are_costs_consistent() is False:
            for edge in self.edges:
                edge.cost = 0 if edge.cost is None else edge.cost

    def __str__(self):
        return " | ".join([f"{edge.nodes[0].element} -{'['+str(edge.cost)+']' if edge.cost is not None else '-'}- "
                           f"{edge.nodes[1].element}" for edge in self.edges])

    # returns [True] if either all edges have or have no costs
    # returns [False] if costs are mixed within graph
    def are_costs_consistent(self) -> bool:
        return all(edge.cost is not None for edge in self.edges) or all(edge.cost is None for edge in self.edges)

    def has_circle(self) -> bool:
        copied_edges = copy(self.edges)
        copied_nodes = copy(self.nodes)
        while copied_edges != set():
            if len({node for node in copied_nodes if node.is_source()}) <= 1:
                return True

            # process to remove source nodes from copied_nodes
            source_edges = {edge for edge in copied_edges if edge.nodes[0].is_source() or edge.nodes[1].is_source()}
            copied_edges = copied_edges.difference(source_edges)
            Graph.carefully_remove_nodes(copied_nodes, [a for edge in source_edges for a in edge.nodes])
        return False

    def remove_edges(self, edges: set[Edge]):
        self.edges = self.edges.difference(edges)
        Graph.carefully_remove_nodes(self.nodes, [remove_node for edge in self.edges for remove_node in edge.nodes])

    # either reduce degree of node or remove it entirely if degree == 0
    @staticmethod
    def carefully_remove_nodes(base_set_of_nodes: set[Node], nodes_to_remove: list[Node]):
        for found in nodes_to_remove:
            found.degree -= 1
            if found.degree == 0:
                base_set_of_nodes.remove(found)

    def reset_degrees(self):
        node_occurrences = [node for edge in self.edges for node in edge.nodes]
        for node in set(node_occurrences):
            node.degree = node_occurrences.count(node)


copied = {"A": Node("A"), "B": Node("B"), "C": Node("C"), "D": Node("D"), "E": Node("E")}
graph = Graph({
    Edge((copied["A"], copied["B"])),
    Edge((copied["C"], copied["B"])),
    Edge((copied["D"], copied["B"])),
    Edge((copied["E"], copied["B"])),
})
print(graph.has_circle())

print(graph)

