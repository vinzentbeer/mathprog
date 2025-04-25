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
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/reference/python.html

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