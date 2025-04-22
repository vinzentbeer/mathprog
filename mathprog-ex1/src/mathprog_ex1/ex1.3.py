import argparse

import gurobipy as gp
from gurobipy import GRB


def build_model(model: gp.Model, n: int, k: int):
    # put your model building code here
    #
    # x = model.addVars(...)
    #
    # if you want to access your variables outside this function, you can use
    # model._x = x
    # to save a reference in the model itself
    #
    # model.addConstrs(...)
    
    # Match result variables
    w1 = model.addVars(n, n, vtype=GRB.BINARY, name="winning variable 1 ")
    w2 = model.addVars(n, n, vtype=GRB.BINARY, name="winning variable 2 ")
    d1 = model.addVars(n, n, vtype=GRB.BINARY, name="draw variable 1 ")
    d2 = model.addVars(n, n, vtype=GRB.BINARY, name="draw variable 2 ")

    # Point variable
    P = model.addVars(n, vtype=GRB.INTEGER, lb=0, name='points')

    # Exactly one outcome per match
    model.addConstrs(w1[i,j] + w1[j,i] + d1[i,j] == 1 for i in range(n) for j in range(n) if i != j)
    model.addConstrs(w2[i,j] + w2[j,i] + d2[i,j] == 1 for i in range(n) for j in range(n) if i != j)

    # Calculate points for each team
    model.addConstrs(P[i] == gp.quicksum(3*w1[i,j]+3*w2[i,j]+d1[i,j]+d2[i,j] for j in range(n) if i!=j) for i in range(n))

    # Order points increasingly
    model.addConstrs(P[i] <= P[i+1] for i in range(n-1))

    # Maximize the points of the k-th team
    model.setObjective(P[k-1] + 1, GRB.MAXIMIZE)

    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", default=18)
    parser.add_argument("--k", default=3)
    args = parser.parse_args()

    model = gp.Model("ex1.3")
    build_model(model, args.n, args.k)

    model.update()
    model.optimize()

    if model.SolCount > 0:
        print(f"obj. value = {model.ObjVal}")
        for v in model.getVars():
            print(f"{v.VarName} = {v.X}")

    model.close()
