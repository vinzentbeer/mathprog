import gurobipy as gp
from gurobipy import GRB
import networkx as nx

def lazy_constraint_callback(model: gp.Model, where):
    # note: you'll need to account for tolerances!
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/concepts/modeling/tolerances.html

    # check integer solutions for feasibility
    if where == GRB.Callback.MIPSOL:
        # get solution values for variables x
        # see https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.cbGetSolution

        # x_values = model.cbGetSolution(model._x)

        if model._formulation == "cec":
            add_violated_cec(model)
        elif model._formulation == "dcc":
            add_violated_dcc(model)

    # check fractional solutions to find violated CECs/DCCs to strengthen the bound
    elif where == GRB.Callback.MIPNODE and model.cbGet(GRB.Callback.MIPNODE_STATUS) == GRB.OPTIMAL:
        # get solution values for variables x
        # see https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.cbGetNodeRel
        
        # x_values = model.cbGetNodeRel(model._x)

        # you may also use different algorithms for integer and fractional separation if you want
        if model._formulation == "cec":
            add_violated_cec(model)
        elif model._formulation == "dcc":
            add_violated_dcc(model)


def add_violated_cec(model: gp.Model):
    # add your CEC separation code here
    pass


def add_violated_dcc(model: gp.Model):
    # add your DCC separation code here
    pass


def create_model(model: gp.Model):
    # --- Common Setup ---
    nodes_V = list(model._original_graph.nodes) # Original nodes V
    edges_E = list(model._original_graph.edges) # Original undirected edges {i,j} in V
    k = model._k

    # Check for node 0 conflict
    if 0 in nodes_V:
        raise ValueError("Original graph nodes cannot include 0 when using implicit artificial root 0.")

    # Directed edges within V
    dir_edges_V = [(i,j) for i,j in edges_E] + [(j,i) for i,j in edges_E]

    # --- Common Variables ---
    # Node selection in V
    x = model.addVars(nodes_V, vtype=GRB.BINARY, name='Node_')
    # Directed edge selection *within* V
    y = model.addVars(dir_edges_V, vtype=GRB.BINARY, name='Edge_')

    # Store references needed by multiple parts (e.g., objective, callbacks)
    model._x = x
    model._y = y # Edges within V only

    # --- Common Constraints ---
    # 1. Select exactly k nodes from V
    model.addConstr(gp.quicksum(x[i] for i in nodes_V) == k, name="SelectKNodes")

    # 2. Link edge selection (within V) to node selection
    model.addConstrs((y[i,j] <= x[i] for i,j in dir_edges_V), name="EdgeImpliesNodeSource")
    model.addConstrs((y[i,j] <= x[j] for i,j in dir_edges_V), name="EdgeImpliesNodeDest")

    # 3. Prevent selecting both directions of an edge within V
    model.addConstrs((y[i,j] + y[j,i] <= 1 for i,j in edges_E), name="OneDirection")

    # --- Common Objective Part ---
    # Base objective: Minimize cost of selected edges *within* V.
    # Specific formulations might add costs for root edges (0,j) later.
    objective = gp.quicksum(y[i,j] * model._original_graph.edges[i,j]['cost'] for i,j in edges_E) + \
                gp.quicksum(y[j,i] * model._original_graph.edges[i,j]['cost'] for i,j in edges_E)
    model.setObjective(objective, GRB.MINIMIZE)


    # --- Formulation Specific Variables and Constraints ---

    if model._formulation == "seq":
        print("Setting up SEQ Formulation...")
        # --- SEQ Specific Variables ---
        # Edges from artificial root 0
        y0j = model.addVars(nodes_V, vtype=GRB.BINARY, name='Edge_0_')
        model._y0j = y0j # Store reference if needed

        # Potential variables (using artificial root 0)
        # node 0 needs potential 0. nodes in V need potentials.
        nodes_V_and_0 = nodes_V + [0]
        u = model.addVars(nodes_V_and_0, lb=0, ub=k+1, vtype=GRB.CONTINUOUS, name='Order_') # Can be INTEGER too
        model._u = u # Store reference if needed

        # --- SEQ Specific Constraints ---
        # Fix root potential
        model.addConstr(u[0] == 0, name="RootPotential")

        # Link root edge selection y0j[j] to node selection x[j]
        model.addConstrs((y0j[j] <= x[j] for j in nodes_V), name="RootEdgeImpliesNode")

        # Each selected node j in V must have exactly one incoming edge (from 0 or from i in V)
        for j in nodes_V:
            incoming_edges = y0j[j] + gp.quicksum(y[i, j] for i, jj in dir_edges_V if jj == j)
            model.addConstr(incoming_edges == x[j], name=f"IncomingDegree_{j}")

        # MTZ constraints (Big-M = k+1 is safer than k)
        M = k + 1 # Or use M=|V| if k=0 is possible and causes issues

        # MTZ for edges within V
        for i, j in dir_edges_V:
            model.addConstr(u[j] >= u[i] + 1 - M * (1 - y[i, j]), name=f"MTZ_{i}_{j}")

        # MTZ for edges from root 0
        for j in nodes_V:
            model.addConstr(u[j] >= u[0] + 1 - M * (1 - y0j[j]), name=f"MTZ_0_{j}") # u[0] is 0

        # Optional: Link potential upper bound to node selection
        # (Helps tighten formulation, forces u[j]=0 if x[j]=0)
        for j in nodes_V:
            model.addConstr(u[j] <= M * x[j], name=f"PotentialBound_{j}")

        # Optional: Add cost of root edges y0j to objective if non-zero
        # root_edge_costs = gp.quicksum(y0j[j] * model._root_costs.get(j, 0) for j in nodes_V)
        # model.setObjective(objective + root_edge_costs, GRB.MINIMIZE) # Adds to existing obj

    elif model._formulation == "scf":
        print("Setting up SCF Formulation...")
        # --- SCF Specific Variables ---
        # Edges from artificial root 0
        y0j = model.addVars(nodes_V, vtype=GRB.BINARY, name='Edge_0_')
        model._y0j = y0j # Store reference

        # Flow variables for ALL directed edges (including from root 0)
        all_dir_edges_with_0 = dir_edges_V + [(0, j) for j in nodes_V]
        f = model.addVars(all_dir_edges_with_0, lb=0.0, name='Flow_')
        model._f = f # Store reference

        # --- SCF Specific Constraints ---
        # Link root edge selection y0j[j] to node selection x[j]
        model.addConstrs((y0j[j] <= x[j] for j in nodes_V), name="RootEdgeImpliesNode")

        # Flow balance for each node j in V: (Inflow - Outflow == Demand)
        for j in nodes_V:
            flow_in = f[0, j] + gp.quicksum(f[i, j] for i, jj in dir_edges_V if jj == j)
            flow_out = gp.quicksum(f[j, l] for jj, l in dir_edges_V if jj == j)
            model.addConstr(flow_in - flow_out == x[j], name=f"FlowBalance_{j}") # Demand = x[j] (1 if selected)

        # Flow balance for the artificial root node 0: (Outflow == Supply)
        model.addConstr(gp.quicksum(f[0, j] for j in nodes_V) == k, name="FlowSource") # Supply = k

        # Capacity constraint linking flow f and edge selection y/y0j
        # M = k is standard, but use k+1 or |V| if k=0 needs flow capacity > 0?
        # Using M=k. If k=0, demand is 0, flow should be 0 anyway.
        capacity_M = k if k > 0 else 1 # Avoid capacity 0 if k=0

        # Capacity for edges within V
        for i, j in dir_edges_V:
             model.addConstr(f[i, j] <= capacity_M * y[i, j], name=f"Capacity_{i}_{j}")

        # Capacity for edges from root 0
        for j in nodes_V:
             model.addConstr(f[0, j] <= capacity_M * y0j[j], name=f"Capacity_0_{j}")

        # Optional: Add cost of root edges y0j to objective if non-zero
        # root_edge_costs = gp.quicksum(y0j[j] * model._root_costs.get(j, 0) for j in nodes_V)
        # model.setObjective(objective + root_edge_costs, GRB.MINIMIZE)

        






        pass
    elif model._formulation == "mcf":

        


        pass
    elif model._formulation == "cec":
        pass
    elif model._formulation == "dcc":
        pass

def get_selected_edge_ids(model: gp.Model) -> list[int]:
    # note that you may need to account for tolerances
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/concepts/modeling/tolerances.html

    # https://docs.gurobi.com/projects/optimizer/en/current/concepts/attributes/examples.html
    return [model._original_graph.edges[edge]["id"] for edge in model._original_graph.edges if model._y[edge].X == 1 or model._y[edge[1],edge[0]].X == 1]