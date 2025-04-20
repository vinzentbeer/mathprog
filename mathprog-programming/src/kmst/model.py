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


    # create common variables
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.addVars

    # Variables for each node
    x = model.addVars(model._original_graph.nodes, vtype=GRB.BINARY)
    # Variables for each edge
    y = model.addVars(model._original_graph.edges, vtype=GRB.BINARY)


    # add reference to relevant variables for later use in callbacks (CEC,DCC)

    model._x = x
    model._y = y

    # create common constraints
    # see, e.g., https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.addConstr

    model.addConstr(gp.quicksum(x) == model._k)
    model.addConstr(gp.quicksum(y) == model._k - 1)

    model.addConstrs(y[i,j] <= x[i] for i,j in model._original_graph.edges)
    model.addConstrs(y[i,j] <= x[j] for i,j in model._original_graph.edges)

    model.setObjective(gp.quicksum(y))

    # create model-specific variables and constraints
    if model._formulation == "seq":
        pass
    elif model._formulation == "scf":
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
    return [model._original_graph.edges[edge]["id"] for edge in model._original_graph.edges if model._y[edge].X == 1]