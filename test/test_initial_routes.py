from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from functools import partial

import solution_output as SO
import evaluators as E
import demand as D
import vehicles as V
import model_run as MR
import initial_routes as IR

import read_csv as reader

# hack to capture stdout to a string, to test it
import io, sys
from contextlib import contextmanager
import os
import filecmp

def test_initial_routes():

    horizon = 20000
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    odpairs = reader.load_demand_from_csv('test/data/demand.csv')
    d     = D.Demand(odpairs,m,horizon)
    m = d.generate_solver_space_matrix(m)
    x_m = d.insert_nodes_for_breaks(m)

    v = V.Vehicles(5,horizon)

    trip_chains_B = IR.initial_routes_2(d,v.vehicles,x_m)
    initial_routes_B = [tcv for tcv in trip_chains_B.values()]
    (assignment,routing,manager) = MR.model_run(d,x_m,v.vehicles,10000,None,initial_routes_B)
    assert assignment
    assert assignment.ObjectiveValue() == 43516

    for vehicle in v.vehicles:
        vehicle_id = vehicle.index
        original_chain = trip_chains_B[vehicle_id]
        index = routing.Start(vehicle_id)
        plan_output = []
        route_time = 0
        while not routing.IsEnd(index):
            # drop 0
            node = manager.IndexToNode(index)
            if node != 0:
                plan_output.append(node)
            index = assignment.Value(routing.NextVar(index))

        # print(original_chain)
        # print(plan_output)
        assert original_chain == plan_output
