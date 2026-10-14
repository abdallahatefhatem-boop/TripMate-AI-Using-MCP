from agent.travel_graph import travel_graph, workflow


def test_graph_nodes_and_edges():
    nodes = workflow.nodes
    assert "flight_agent" in nodes
    assert "hotel_agent" in nodes
    assert "itinerary_agent" in nodes
    assert "final_agent" in nodes


def test_travel_graph_compilation():
    assert travel_graph is not None
