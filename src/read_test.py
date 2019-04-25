from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from functools import partial

import argparse
#import os

import read_csv as reader
import vehicles as V
import demand as D
import evaluators as E

def main():
    """Entry point of the program."""
    parser = argparse.ArgumentParser(description='Solve assignment of truck load routing problem, give hours of service rules and a specified list of origins and destinations')
    parser.add_argument('-m,--matrixfile', type=str, dest='matrixfile',
                        help='CSV file for travel matrix (distances)')
    parser.add_argument('-d,--demandfile', type=str, dest='demand',
                        help='CSV file for demand pairs (origin, dest, time windows)')
    parser.add_argument('--speed', type=float, dest='speed', default=55.0,
                        help='Average speed, miles per hour.  Default is 55 (miles per hour).  Distance unit should match that of the matrix of distances.  The time part should be per hours')
    parser.add_argument('--maxtime', type=float, dest='horizon', default=10080,
                        help='Max time in minutes.  Default is 7 days, which is 10080 minutes..')

    parser.add_argument('-v,--vehicles', type=int, dest='numvehicles', default=100,
                        help='Number of vehicles to create.  Default is 100.')
    parser.add_argument('--pickup_time', type=int, dest='pickup_time', default=15,
                        help='Pick up time in minutes.  Default is 15 minutes.')
    parser.add_argument('--dropoff_time', type=int, dest='dropoff_time', default=15,
                        help='Drop off time in minutes.  Default is 15 minutes.')

    args = parser.parse_args()
    matrix = reader.load_matrix_from_csv(args.matrixfile)
    assert (matrix.ndim == 2)
    assert (matrix.size == 100 * 100)
    assert (matrix.iloc[0,0] == 0)
    assert (matrix.iloc[0,1] == 875)
    assert (matrix.iloc[1,0] == 874)
    # print(matrix.head())
    assert (len(matrix[0]) == 100)
    # will need a simple 2D array for calling into ortools...safer that way
    # dist_lookup = reader.make_simple_matrix(matrix)
    # print(dist_lookup[0,1])

    minutes_matrix = reader.travel_time(args.speed/60,matrix)
    # print(minutes_matrix.head())
    # tests?

    demand = D.Demand(args.demand,args.horizon)

    # print(demand.head())


    # vehicles:
    vehicles = V.Vehicles(args.numvehicles)

    # data is in, now process and setup solver

    # Create the routing index manager.
    # note that depot_index isn't an int, apparently.  have to cast
    # print(len(matrix), args.numvehicles, int(vehicles.vehicles[0].depot_index))
    # also, assuming here that all depots are in the same place
    # and that vehicles all return to the same depot
    manager = pywrapcp.RoutingIndexManager(
        int(demand.get_number_nodes() + 1 ), # add 1 for 1 depot.
        int(args.numvehicles),
        int(vehicles.vehicles[0].depot_index))


    # Set model parameters
    # model_parameters = pywrapcp.DefaultRoutingModelParameters()
    # Create Routing Model.
    # routing = pywrapcp.RoutingModel(manager,model_parameters)
    routing = pywrapcp.RoutingModel(manager)
    #solver = routing.solver()

    # Define cost of each arc using travel time + service time
    time_callback = partial(E.create_time_callback(minutes_matrix,
                                                   demand),
                            manager)

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    # might want to remove service time from the above

    # Add Time dimension for time windows, precedence constraints
    dimension_name = 'Time'
    routing.AddDimension(
        transit_callback_index, # same "cost" evaluator as above
        args.horizon,  # slack for full range
        args.horizon,  # max time is end of time horizon
        True,  # start cumul to zero
        dimension_name)
    time_dimension = routing.GetDimensionOrDie(dimension_name)
    # this is new in v7.0, not sure what it does yet
    # time_dimension.SetGlobalSpanCostCoefficient(100)
    # Define Transportation Requests.

    # [START pickup_delivery_constraint]
    print('apply pickup and delivery constraints')
    for idx in demand.demand.index:
        record = demand.demand.iloc[idx]
        pickup_index = manager.NodeToIndex(record.origin)
        delivery_index = manager.NodeToIndex(record.destination)
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) ==
            routing.VehicleVar(delivery_index))
        routing.solver().Add(
            time_dimension.CumulVar(pickup_index) <=
            time_dimension.CumulVar(delivery_index))


    # # [START time_window_constraint]
    # print('apply time window  constraints')
    # for idx in demand.demand.index:
    #     record = demand.demand.iloc[idx]
    #     pickup_index = manager.NodeToIndex(record.origin)
    #     early = int(record.early)
    #     late = int(record.late)
    #     time_dimension.CumulVar(pickup_index).SetRange(early, late)

    # Setting first solution heuristic.
    # [START parameters]
    print('set up model parameters')
    # [START parameters]
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)

    # Disabling path Large Neighborhood Search is the default behaviour.  enable
    # parameters.local_search_operators.use_path_lns = pywrapcp.BOOL_TRUE
    # parameters.local_search_operators.use_inactive_lns = pywrapcp.BOOL_TRUE
    # Routing: forbids use of TSPOpt neighborhood,
    # parameters.local_search_operators.use_tsp_opt = pywrapcp.BOOL_FALSE
    # set a time limit
    # parameters.time_limit.seconds = 5 * 60   # 5 minutes
    # sometimes helps with difficult solutions
    # parameters.lns_time_limit_ms = 1000  # 1000 milliseconds
    # i think this is the default
    # parameters.use_light_propagation = False
    # set to true to see the dump of search iterations
    search_parameters.log_search = pywrapcp.BOOL_TRUE

    # add disjunctions to deliveries to make it not fail
    penalty = 1000000  # The cost for dropping a node from the plan.
    droppable_nodes = [routing.AddDisjunction([manager.NodeToIndex(c)], penalty) for c in demand.get_node_list()]


    print('Calling the solver')
    # [START solve]
    assignment = routing.SolveWithParameters(search_parameters)
    # [END solve]

    if assignment:
        ## save the assignment, (Google Protobuf format)
        #save_file_base = os.path.realpath(__file__).split('.')[0]
        #if routing.WriteAssignment(save_file_base + '_assignment.ass'):
        #    print('succesfully wrote assignment to file ' + save_file_base +
        #          '_assignment.ass')

        print('The Objective Value is {0}'.format(assignment.ObjectiveValue()))


    else:
        print('assignment failed')



if __name__ == '__main__':
    main()
