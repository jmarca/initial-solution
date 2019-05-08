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
    d = D.Demand('test/data/demand.csv',horizon)
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    m = d.generate_solver_space_matrix(m)
    m_m = reader.travel_time(1,m)

    v = V.Vehicles(5)
    demand_callback = E.create_demand_callback(m_m.index,d)
    time_callback = E.create_time_callback(m_m,d)
    dist_callback = E.create_dist_callback(m,d)

    manager = pywrapcp.RoutingIndexManager(
        d.get_number_nodes() + 1, # add 1 for 1 depot.
        len(v.vehicles),
        v.vehicles[0].depot_index)
    routing = pywrapcp.RoutingModel(manager)

    transit_callback_index = routing.RegisterTransitCallback(
        partial(time_callback,manager)
    )
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    time_dimension_name = 'Time'
    routing.AddDimension(
        transit_callback_index, # same "cost" evaluator as above
        horizon,  # slack for full range
        horizon,  # max time is end of time horizon
        True,  # start cumul to zero
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
    with redirected(out=out, err=err):
        out.flush()
        err.flush()
        SO.print_solution(d,partial(dist_callback,manager),v,manager,routing,assignment)
        output = out.getvalue()

        expected_output = """Objective: 19246
Breaks:
Routes:
Route for vehicle 0:
node 0, mapnode 0, Load 0,  Time(0:00:00,0:00:00) Slack(1050,1770) Link time(0:00:00) Link distance(0 mi)
 ->node 4, mapnode 5, Load 0,  Time(1 day, 9:00:00,1 day, 21:00:00) Slack(0,16417) Link time(15:30:00) Link distance(930 mi)
 ->node 9, mapnode 2, Load 1,  Time(2 days, 5:49:00,13 days, 15:26:00) Slack(0,0) Link time(20:49:00) Link distance(1234 mi)
 -> 0 Load(0)  Time(2 days, 11:43:00,13 days, 21:20:00)  Link time(5:54:00) Link distance(339 mi)
Distance of the route: 2503 miles
Loads served by route: 1
Time of the route: 2 days, 11:43:00

Route for vehicle 1:
node 0, mapnode 0, Load 0,  Time(0:00:00,0:00:00) Slack(1050,1770) Link time(0:00:00) Link distance(0 mi)
 ->node 2, mapnode 5, Load 0,  Time(1 day, 9:00:00,1 day, 21:00:00) Slack(0,2558) Link time(15:30:00) Link distance(930 mi)
 ->node 7, mapnode 4, Load 1,  Time(3 days, 4:51:00,4 days, 23:29:00) Slack(0,0) Link time(1 day, 19:51:00) Link distance(2616 mi)
 ->node 1, mapnode 7, Load 0,  Time(4 days, 9:00:00,5 days, 21:00:00) Slack(0,11265) Link time(21:31:00) Link distance(1276 mi)
 ->node 6, mapnode 9, Load 1,  Time(4 days, 22:45:00,12 days, 18:30:00) Slack(0,0) Link time(13:45:00) Link distance(810 mi)
 -> 0 Load(0)  Time(6 days, 1:35:00,13 days, 21:20:00)  Link time(1 day, 2:50:00) Link distance(1595 mi)
Distance of the route: 7227 miles
Loads served by route: 2
Time of the route: 6 days, 1:35:00

Route for vehicle 2:
node 0, mapnode 0, Load 0,  Time(0:00:00,0:00:00) Slack(3018,3415) Link time(0:00:00) Link distance(0 mi)
 ->node 5, mapnode 8, Load 0,  Time(3 days, 9:00:00,3 days, 15:37:00) Slack(0,0) Link time(1 day, 6:42:00) Link distance(1842 mi)
 ->node 10, mapnode 3, Load 1,  Time(5 days, 13:04:00,5 days, 19:41:00) Slack(0,0) Link time(2 days, 4:04:00) Link distance(3109 mi)
 ->node 3, mapnode 1, Load 0,  Time(5 days, 14:23:00,5 days, 21:00:00) Slack(0,7556) Link time(1:19:00) Link distance(64 mi)
 ->node 8, mapnode 6, Load 1,  Time(7 days, 13:46:00,12 days, 19:42:00) Slack(0,0) Link time(1 day, 23:23:00) Link distance(2828 mi)
 -> 0 Load(0)  Time(8 days, 15:24:00,13 days, 21:20:00)  Link time(1 day, 1:38:00) Link distance(1523 mi)
Distance of the route: 9366 miles
Loads served by route: 1
Time of the route: 8 days, 15:24:00

Route for vehicle 3:
node 0, mapnode 0, Load 0,  Time(0:00:00,0:00:00) Slack(0,20000) Link time(0:00:00) Link distance(0 mi)
 -> 0 Load(0)  Time(0:00:00,13 days, 21:20:00)  Link time(0:00:00) Link distance(0 mi)
Distance of the route: 0 miles
Loads served by route: 0
Time of the route: 0:00:00

Route for vehicle 4:
node 0, mapnode 0, Load 0,  Time(0:00:00,0:00:00) Slack(0,20000) Link time(0:00:00) Link distance(0 mi)
 -> 0 Load(0)  Time(0:00:00,13 days, 21:20:00)  Link time(0:00:00) Link distance(0 mi)
Distance of the route: 0 miles
Loads served by route: 0
Time of the route: 0:00:00

Total Distance of all routes: 19096 miles
Total Loads picked up by all routes: 4
Total Time of all routes: 17 days, 4:42:00
"""
        assert output == expected_output
