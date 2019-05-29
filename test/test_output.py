from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from functools import partial

import solution_output as SO
import evaluators as E
import demand as D
import vehicles as V

import read_csv as reader

# hack to capture stdout to a string, to test it
import io, sys
from contextlib import contextmanager
import os
import filecmp

output_file = 'test_output.txt'
second_output_file = 'test_output_1.txt'
expected_file = 'test/data/expected_test_output.txt'

class MockArgs():

    def __init__(self):
        self.speed = 60
        self.summary_output = output_file

@contextmanager
def redirected(out=sys.stdout, err=sys.stderr):
    saved = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        yield
    finally:
        sys.stdout, sys.stderr = saved

def test_output():

    horizon = 20000
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    odpairs = reader.load_demand_from_csv('test/data/demand.csv')
    d     = D.Demand(odpairs,m,horizon)
    m = d.generate_solver_space_matrix(m)
    # just go with 60 mph for test, m is mm

    v = V.Vehicles(5,horizon)
    manager = pywrapcp.RoutingIndexManager(
        len(m.index),
        len(v.vehicles),
        v.vehicles[0].depot_index)
    demand_callback = E.create_demand_callback(m.index,d)
    time_callback = E.create_time_callback2(m,d)
    dist_callback = E.create_dist_callback(m,d)

    routing = pywrapcp.RoutingModel(manager)

    transit_callback_index = routing.RegisterTransitCallback(
        partial(time_callback,manager)
    )
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    count_dimension_name = 'Count'
    routing.AddConstantDimension(
        1, # increment by one every time
        len(m.index),  # max count is visit all the nodes
        True,  # set count to zero
        count_dimension_name)
    count_dimension = routing.GetDimensionOrDie(count_dimension_name)

    time_dimension_name = 'Time'
    routing.AddDimension(
        transit_callback_index, # same "cost" evaluator as above
        0,  # no slack
        horizon,  # max time is end of time horizon
        False,  # start cumul to zero
        time_dimension_name)
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)

    demand_evaluator_index = routing.RegisterUnaryTransitCallback(
        partial(demand_callback, manager)
    )
    cap_dimension_name = 'Capacity'
    vehicle_capacities = [veh.capacity for veh in v.vehicles]
    routing.AddDimensionWithVehicleCapacity(
        demand_evaluator_index,
        0,  # null capacity slack
        vehicle_capacities,
        True,  # start cumul to zero
        cap_dimension_name)

    for idx in d.demand.index:
        record = d.demand.loc[idx]
        pickup_index = manager.NodeToIndex(record.origin)
        delivery_index = manager.NodeToIndex(record.destination)
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) ==
            routing.VehicleVar(delivery_index))
        routing.solver().Add(
            time_dimension.CumulVar(pickup_index) <=
            time_dimension.CumulVar(delivery_index))
    print('apply time window  constraints')
    for idx in d.demand.index:
        record = d.demand.loc[idx]
        pickup_index = manager.NodeToIndex(record.origin)
        early = int(record.early)
        late = int(record.late)
        time_dimension.CumulVar(pickup_index).SetRange(early, late)
        routing.AddToAssignment(time_dimension.SlackVar(pickup_index))
    # Add time window constraints for each vehicle start node
    # and 'copy' the slack var in the solution object (aka Assignment) to print it
    for vehicle in v.vehicles:
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(vehicle.time_window[0],
                                                vehicle.time_window[1])
        routing.AddToAssignment(time_dimension.SlackVar(index))

    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)
    parameters.time_limit.seconds =  60
    # add disjunctions to deliveries to make it not fail
    penalty = 10000000  # The cost for dropping a node from the plan.
    droppable_nodes = [routing.AddDisjunction([manager.NodeToIndex(c)], penalty) for c in d.get_node_list()]

    assignment = routing.SolveWithParameters(parameters)

    assert assignment

    out = io.StringIO()
    err = io.StringIO()
    args = MockArgs()
    with redirected(out=out, err=err):
        out.flush()
        err.flush()
        SO.print_solution(d,m,m,
                          v,manager,routing,assignment,horizon,
                          0,args
        )
        output = out.getvalue()

        expected_output = ""
        assert output == expected_output
        assert filecmp.cmp(output_file,expected_file)

    # make sure output file was created as directed
    assert os.path.exists(args.summary_output)
    assert os.path.exists(output_file)

    # do it again, and this time there should be a _1 version of args.summary_output
    assert not os.path.exists(second_output_file)
    out = io.StringIO()
    err = io.StringIO()
    with redirected(out=out, err=err):
        out.flush()
        err.flush()
        SO.print_solution(d,m,m,
                          v,manager,routing,assignment,horizon,
                          0,args
        )
        output = out.getvalue()

        expected_output = ""
        assert output == expected_output
    # created alternate named file
    assert os.path.exists(second_output_file)
    assert filecmp.cmp(output_file,second_output_file)

    os.unlink(output_file)
    os.unlink(second_output_file)
