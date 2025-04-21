from pyvis.network import Network
import networkx as nx

from model import get_selected_edge_ids

def plot_graph(model, G, args):
    # Build MST subgraph
    selected_edges = set(get_selected_edge_ids(model))
    selected_edge_tuples = [e for e in G.edges if G.edges[e]["id"] in selected_edges]
    mst_subgraph = G.edge_subgraph(selected_edge_tuples).copy()

    # Initialize PyVis network
    net = Network(notebook=False, height="800px", width="100%", bgcolor="#ffffff", font_color="black", directed=False)

    # Add nodes (highlight MST nodes)
    for node in G.nodes:
        color = 'orange' if node in mst_subgraph.nodes else 'lightgray'
        net.add_node(node, label=str(node), color=color)

    # Add edges (highlight MST edges)
    for u, v in G.edges:
        is_mst = (u, v) in selected_edge_tuples or (v, u) in selected_edge_tuples
        color = 'red' if is_mst else '#cccccc'
        width = 4 if is_mst else 1
        label = str(G[u][v]['cost'])
        net.add_edge(u, v, color=color, width=width, title=f"Weight: {label}", label=label)

    # Enable dragging & physics
    net.toggle_physics(True)

    # Save and show
    html_path = "k_mst_interactive.html"
    net.save_graph(html_path)

    # Optional: open in browser
    import webbrowser
    webbrowser.open(html_path)