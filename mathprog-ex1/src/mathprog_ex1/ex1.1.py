import argparse
import os
from pathlib import Path

import gurobipy as gp
import networkx as nx
from gurobipy import GRB


def read_instance_file(filename: str | os.PathLike) -> nx.Graph:
    with open(Path(filename), mode="r", encoding="utf-8") as f:
        n_nodes = int(f.readline())
        n_edges = int(f.readline())

        graph = nx.Graph()

        # skip comment line
        f.readline()

        # read node lines
        for _ in range(n_nodes):
            line = f.readline()
            node_id, name, supply_demand = line.split()
            graph.add_node(int(node_id), name=name, supply_demand=int(supply_demand))

        # skip comment line
        f.readline()

        # read edge lines
        for _ in range(n_edges):
            line = f.readline()
            (
                edge_id,
                node_1,
                node_2,
                transport_cost,
                build_cost_1,
                build_cost_2,
                capacity_1,
                capacity_2,
            ) = line.split()
            graph.add_edge(
                int(node_1),
                int(node_2),
                id=int(edge_id),
                transport_cost=int(transport_cost),
                build_cost_1=int(build_cost_1),
                build_cost_2=int(build_cost_2),
                capacity_1=int(capacity_1),
                capacity_2=int(capacity_2),
            )

        return graph


def build_model(model: gp.Model, graph: nx.Graph):
    # note that nodes are 1-indexed

    # put your model building code here
    #
    # x = model.addVars(...)
    #
    # if you want to access your variables outside this function, you can use
    # model._x = x
    # to save a reference in the model itself
    #
    # model.addConstrs(...)

    x1 = model.addVars(
        graph.edges,
        name="x1",
        vtype=GRB.BINARY,
    )
    x2 = model.addVars(
        graph.edges,
        name="x2",
        vtype=GRB.BINARY,
    )

    f = model.addVars(
        [(i, j) for i, j in graph.edges()] + [(j, i) for i, j in graph.edges()],
        vtype=GRB.CONTINUOUS,
        lb=0.0,
        name="f")
    
    model.addConstrs((x1[i,j] + x2[i,j] <= 1 for i,j in graph.edges), name="at most one link variant")
    model.addConstrs((gp.quicksum(f[i,j] - f[j,i] for j in graph.neighbors(i)) == graph.nodes[i]["supply_demand"] for i in graph.nodes), name="flow conservation")
    model.addConstrs((f[i,j] + f[j,i] <= graph[i][j]["capacity_1"] * x1[i, j] + graph[i][j]["capacity_2"] * x2[i, j] for i, j in graph.edges), name="flow <= capacity")

    model.setObjective(gp.quicksum(graph[i][j]["transport_cost"] * f[i,j] +
                                   graph[i][j]["transport_cost"] * f[j,i] +
                                   graph[i][j]["build_cost_1"] * x1[i,j] +
                                   graph[i][j]["build_cost_2"] * x2[i,j]  for i, j in graph.edges), GRB.MINIMIZE)

   
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", default="instances/ex1.1-instance.dat")
    args = parser.parse_args()

    graph = read_instance_file(args.filename)

    model = gp.Model("ex1.1")
    build_model(model, graph)

    model.update()
    model.optimize()

    if model.SolCount > 0:
        print(f"obj. value = {model.ObjVal}")
        for v in model.getVars():
            print(f"{v.VarName} = {v.X}")

    model.close()
