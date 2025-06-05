import gurobipy as gp
from gurobipy import GRB
import networkx as nx

def lazy_constraint_callback(model: gp.Model, where):
    # note: you'll need to account for tolerances!
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/concepts/modeling/tolerances.html
    model._lazy_constrs_added += 1 #should really add this only when succressful
    # check integer solutions for feasibility
    if where == GRB.Callback.MIPSOL:
        # get solution values for variables x
        # see https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.cbGetSolution

        model._y_values = model.cbGetSolution(model._y)

        if model._formulation == "cec":
            add_violated_cec(model)
        elif model._formulation == "dcc":
            model._x_values = model.cbGetSolution(model._x)
            model._r_value = model.cbGetSolution(model._r)
            add_violated_dcc(model)

    # check fractional solutions to find violated CECs/DCCs to strengthen the bound
    elif where == GRB.Callback.MIPNODE and model.cbGet(GRB.Callback.MIPNODE_STATUS) == GRB.OPTIMAL:
        # get solution values for variables x
        # see https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.cbGetNodeRel
        
        model._y_values = model.cbGetNodeRel(model._y)

        # you may also use different algorithms for integer and fractional separation if you want
        if model._formulation == "cec":
            add_violated_cec(model)
        elif model._formulation == "dcc":
            model._x_values = model.cbGetNodeRel(model._x)
            model._r_value = model.cbGetNodeRel(model._r)
            add_violated_dcc(model)


def add_violated_cec(model: gp.Model):
    # Build a graph
    G = nx.Graph()
    for (i,j), val in model._y_values.items():
        if val > 1e-5:
            G.add_edge(i, j, weight=val)

    # Detect cycles
    try:
        cycle_edges = nx.find_cycle(G)
    except nx.NetworkXNoCycle:
        return

    # Add lazy constraint to eliminate this cycle
    model.cbLazy(gp.quicksum(model._y[i,j] + model._y[j,i] for i,j in cycle_edges) <= len(cycle_edges) - 1)

    pass


def add_violated_dcc(model: gp.Model):
    # Build graph
    G = nx.DiGraph()
    for (i, j), val in model._y_values.items():
        G.add_edge(i, j, capacity=val)
            
    G.add_node(0)
    root = max(model._r_value, key=model._r_value.get)
    # root_val = max(model._r_value.values())
    # G.add_edge(0, root, capacity=root_val)
    # print(root, root_val)
    for i, val in model._r_value.items():
        G.add_edge(0, i, capacity=val)

    for t in G:
        if t==0 or t==root:
            continue

        cut_val, (A, B) = nx.minimum_cut(G, 0, t)
        if cut_val + 1e-5 < model._x_values[t]:
            cut_edges = [(u,v) for (u,v) in model._y_values if u in A and v in B]
            model.cbLazy(gp.quicksum(model._y[u,v] for (u,v) in cut_edges) >= model._x[t])
            return
    pass


def create_model(model: gp.Model):
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/reference/python.html
    
    model._lazy_constrs_added = 0

    nodes: nx.Graph.nodes = model._original_graph.nodes
    edges: nx.Graph.edges = model._original_graph.edges
    k = model._k
    
    dir_edges = [(i,j) for i,j in edges] + [(j,i) for i,j in edges]

    # create common variables
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.addVars

    # Variables for each node
    x = model.addVars(nodes, vtype=GRB.BINARY, name='Node ')
    # Variables for each edge
    y = model.addVars(dir_edges, vtype=GRB.BINARY, name='Edge ')


    # add reference to relevant variables for later use in callbacks (CEC,DCC)

    model._x = x
    model._y = y

    # create common constraints
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.addConstr

    # Number constraints
    model.addConstr(gp.quicksum(x) == k)
    model.addConstr(gp.quicksum(y) == k - 1)

    # Linking nodes and edges
    model.addConstrs(y[i,j] <= x[i] for i,j in dir_edges)
    model.addConstrs(y[i,j] <= x[j] for i,j in dir_edges)

    # Only one directional edge
    model.addConstrs(y[i,j] + y[j,i] <= 1 for i,j in edges)

    # At most one incoming edge per node
    model.addConstrs(gp.quicksum(y[i,j] for i in nodes if (i,j) in dir_edges) <= x[j] for j in nodes)

    # Minimize edge weights
    model.setObjective(gp.quicksum((y[i,j] + y[j,i]) * edges[i,j]['cost'] for i,j in edges))

    # create model-specific variables and constraints
    if model._formulation == "seq":
        
        # Sequent variables
        u = model.addVars(nodes, lb=0, ub=k+1, vtype=GRB.INTEGER, name='Order ')

        """
        Initial solution with artificial root node, guess it is not necessary

        # Artificial root node (serves as a 'selector')
        r = model.addVars(nodes, vtype=GRB.BINARY, name='Root ')

        # One edge from root node to any other node (The node to which it points is the real root node)
        model.addConstr(gp.quicksum(r) == 1)
        model.addConstrs(r[i] <= x[i] for i in nodes)

        # Root sequent
        model.addConstrs(u[i] <= k * (1 - r[i]) for i in nodes)
        """

        # Sequent
        model.addConstrs(u[i] + 1 <= u[j] + k * (1 - y[i,j]) for i,j in dir_edges)
        

        pass
    elif model._formulation == "scf":

        dir_edges_with_0 = dir_edges + [(0, j) for j in nodes]

        # Flow variable
        f = model.addVars(dir_edges_with_0, lb=0, vtype=GRB.CONTINUOUS, name='Flow ')

        # Artificial root node (serves as a 'selector')
        r = model.addVars(nodes, vtype=GRB.BINARY, name='Root ')

        # One edge from root node to any other node (The node to which it points is the real root node)
        model.addConstr(gp.quicksum(r) == 1)
        model.addConstrs(r[i] <= x[i] for i in nodes)

        # Flow constraints
        model.addConstrs(f[0,j] == k * r[j] for j in nodes)
        model.addConstrs(gp.quicksum(f[i,j] for i, l in dir_edges_with_0 if l==j) -
                         gp.quicksum(f[j,l] for i, l in dir_edges_with_0 if i==j) == x[j] for j in nodes)
        model.addConstrs(f[i,j] <= k * y[i,j] for i,j in dir_edges)

        pass

    elif model._formulation == "mcf":

        dir_edges_with_0 = dir_edges + [(0, j) for j in nodes]
        commodity_vars = [(i,j,c) for i,j in dir_edges_with_0 for c in nodes]

        # Flow variable
        f = model.addVars(commodity_vars, lb=0, vtype=GRB.BINARY, name='Flow ')

        # Artificial root node (serves as a 'selector')
        r = model.addVars(nodes, vtype=GRB.BINARY, name='Root ')

        # One edge from root node to any other node (The node to which it points is the real root node) (all hail the real root node)
        model.addConstr(gp.quicksum(r) == 1)
        model.addConstrs(r[i] <= x[i] for i in nodes)

        # Flow constraints
        model.addConstrs(gp.quicksum(f[0,j,c] for j in nodes) == x[c] for c in nodes)   # An ominous source node 0 sends out k packages, addressed to each node that is included in the MST
        model.addConstrs(f[0,i,c] <= r[i] for i in nodes for c in nodes)                # The first address for all packages is always the artificial root node in the graph
        model.addConstrs(gp.quicksum(f[i,c,c] for i,j2 in dir_edges if j2==c) == x[c]-r[c] for c in nodes)  # Each included non-root node in the MST consumes one package
        model.addConstrs(gp.quicksum(f[i,j,c] for (i, j2) in dir_edges_with_0 if j2 == j) -     # Packages are forwarded, if current node is not the destination
                         gp.quicksum(f[j,i,c] for (j2, i) in dir_edges_with_0 if j2 == j) == 0 for j in nodes for c in nodes if j!=c)  # This also ensures, that packages cannot backflow to 0
        model.addConstrs(f[i,j,c] <= y[i,j] for (i,j) in dir_edges for c in nodes)      # If there is flow on an edge, include it in the MST
        
        pass

    elif model._formulation == "cec":

        # cycles = nx.simple_cycles(model._original_graph)

        # for c in cycles:
        #     model.addConstr(gp.quicksum(y[i,j] + y[j,i] for (i,j) in zip(c, c[1:] + [c[0]])) <= len(c) - 1)

        pass
    elif model._formulation == "dcc":

        # Root node definition
        r = model.addVars(nodes, vtype=GRB.BINARY, name='Root ')
        model.addConstr(gp.quicksum(r) == 1)
        model.addConstrs(r[i] <= x[i] for i in nodes)
        model._r = r

        # If a node is selected and not the root node, then at least one node is incoming
        model.addConstrs(x[j] - r[j] <= gp.quicksum(y[i,j] for i,l in dir_edges if l==j) for j in nodes)

        pass

def get_selected_edge_ids(model: gp.Model) -> list[int]:
    # note that you may need to account for tolerances
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/concepts/modeling/tolerances.html

    # https://docs.gurobi.com/projects/optimizer/en/current/concepts/attributes/examples.html
    return [model._original_graph.edges[edge]["id"] for edge in model._original_graph.edges if model._y[edge].X == 1 or model._y[edge[1],edge[0]].X == 1]