from graph import *
import pandas

def kruskal_algorithm(input_graph: Graph) -> Graph:
    copied_graph = copy(input_graph)
    minimal_edges = set()
    for _ in copied_graph.edges:
        minimal_costly_edge = {edge for edge in copied_graph.edges if
                               edge.cost == min([edge.cost for edge in copied_graph.edges])}

        for i in range(len(minimal_costly_edge) - 1):
            minimal_costly_edge.pop() # should only contain one object

        copied_graph.remove_edges(minimal_costly_edge)
        for edge in minimal_costly_edge:
            minimal_edges.add(edge)

        if Graph(minimal_edges).has_circle():
            minimal_edges = minimal_edges.difference(minimal_costly_edge)
            continue

        if len(minimal_edges) == len(input_graph.edges) - 1:
            return Graph(minimal_edges)

    return Graph(minimal_edges)


n = {1: Node("1"), 2: Node("2"), 3: Node("3"), 4: Node("4"), 5: Node("5"), 6: Node("6")}
test = Graph({
    # Edge((n[1], n[2]), 6),
    # Edge((n[1], n[3]), 5),
    # Edge((n[1], n[4]), 6),
    # Edge((n[1], n[6]), 2),
    # Edge((n[2], n[3]), 4),
    # Edge((n[3], n[4]), 1),
    # Edge((n[3], n[5]), 3),
    # Edge((n[4], n[5]), 2),
    # Edge((n[4], n[6]), 4),
    # Edge((n[5], n[6]), 7),
    Edge((n[1], n[2]), 2),
    Edge((n[1], n[5]), 3),
    Edge((n[2], n[5]), 1),
    Edge((n[2], n[3]), 2),
    Edge((n[3], n[4]), 3),
    Edge((n[4], n[5]), 1),
})

result_graph = kruskal_algorithm(test)
print(result_graph)
