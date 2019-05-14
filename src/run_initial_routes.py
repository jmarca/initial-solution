from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from functools import partial
import math
import numpy as np
import pickle

import argparse
#import os

import read_csv as reader
import vehicles as V
import demand as D
import evaluators as E
import solution_output as SO

import initial_routes as IR


def main():
    """Entry point of the program."""
    parser = argparse.ArgumentParser(description='Solve assignment of truck load routing problem, give hours of service rules and a specified list of origins and destinations')
    # parser.add_argument('--resume_file',type=str,dest='resumefile',
    #                     help="resume a failed solver run from this file")
    parser.add_argument('-m,--matrixfile', type=str, dest='matrixfile',
                        help='CSV file for travel matrix (distances)')
    parser.add_argument('-d,--demandfile', type=str, dest='demand',
                        help='CSV file for demand pairs (origin, dest, time windows)')
    parser.add_argument('-o,--vehicleoutput', type=str, dest='vehicle_output', default='vehicle_output.csv',
                        help='CSV file for dumping output')
    parser.add_argument('--demandoutput', type=str, dest='demand_output', default='demand_output.csv',
                        help='CSV file for dumping output for demand details')
    parser.add_argument('--speed', type=float, dest='speed', default=55.0,
                        help='Average speed, miles per hour.  Default is 55 (miles per hour).  Distance unit should match that of the matrix of distances.  The time part should be per hours')
    parser.add_argument('--maxtime', type=int, dest='horizon', default=10080,
                        help='Max time in minutes.  Default is 10080 minutes, which is 7 days.')

    parser.add_argument('-v,--vehicles', type=int, dest='numvehicles', default=100,
                        help='Number of vehicles to create.  Default is 100.')
    parser.add_argument('--pickup_time', type=int, dest='pickup_time', default=15,
                        help='Pick up time in minutes.  Default is 15 minutes.')
    parser.add_argument('--dropoff_time', type=int, dest='dropoff_time', default=15,
                        help='Drop off time in minutes.  Default is 15 minutes.')

    parser.add_argument('-t, --timelimit', type=int, dest='timelimit', default=5,
                        help='Maximum run time for solver, in minutes.  Default is 5 minutes.')

    parser.add_argument('--narrow_destination_timewindows', type=bool,
                        dest='destination_time_windows',
                        default=True,
                        help="If true, limit destination node time windows based on travel time from corresponding origin.  If false, destination nodes time windows are 0 to args.horizon.  Default true (limit the time window).")

    parser.add_argument('--drive_dim_start_value',type=int,dest='drive_dimension_start_value',default=1000,
                        help="Due to internal solver mechanics, the drive dimension can't go below zero (it gets truncated at zero).  So to get around this, the starting point for the drive time dimension has to be greater than zero.  The default is 1000.  Change it with this variable")

    parser.add_argument('--debug', type=bool, dest='debug', default=False,
                        help="Turn on some print statements.")
    args = parser.parse_args()

    print('read in distance matrix')
    matrix = reader.load_matrix_from_csv(args.matrixfile)
    minutes_matrix = reader.travel_time(args.speed/60,matrix)

    print('read in demand data')
    d = D.Demand(args.demand,minutes_matrix,args.horizon)

    # convert nodes to solver space from input map space
    mm = d.generate_solver_space_matrix(minutes_matrix,args.horizon)

    # create dummy nodes for breaks
    expanded_mm = d.insert_nodes_for_breaks(mm)

    # copy new nodes to distance matrix
    expanded_m = reader.travel_time(60/args.speed,expanded_mm)
    # print('original matrix of',len(matrix.index),'expanded to ',len(expanded_m.index))

    # vehicles:
    vehicles = V.Vehicles(args.numvehicles,args.horizon)

    # Create the routing index manager.

    # number of nodes is now given by the travel time matrix
    # probably should refactor to put time under control of
    # demand class
    num_nodes = len(expanded_mm.index)
    print('After augmenting network with break nodes, solving with ',num_nodes,'nodes')
    #print(d.demand.loc[d.demand.feasible,:])
    print(d.demand.loc[:,['from_node',
                          'to_node',
                          'early',
                          'late',
                          'pickup_time',
                          'dropoff_time',
                          'round_trip',
                          'depot_origin',
                          'earliest_destination',
                          'feasible',
                          'origin',
                          'destination']])


    # print(expanded_mm)
    # assuming here that all depots are in the same place
    # and that vehicles all return to the same depot
    manager = pywrapcp.RoutingIndexManager(
        num_nodes,
        len(vehicles.vehicles),
        vehicles.vehicles[0].depot_index)


    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)
    #solver = routing.solver()

    print('creating time callback for solver')
    # Define cost of each arc using travel time + service time

    # this version adds "service times" of 10 hours at breaks nodes.
    # FIXME need to fix the callback to also handle 30 min breaks
    time_callback = partial(E.create_time_callback2(expanded_mm, d),
                            manager)

    print('registering callbacks with routing solver')
    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    # might want to remove service time from the above

    print('create count dimension')
    # Add Count dimension for count windows, precedence constraints
    count_dimension_name = 'Count'
    routing.AddConstantDimension(
        1, # increment by one every time
        len(expanded_mm.index),  # max count is visit all the nodes
        True,  # set count to zero
        count_dimension_name)
    count_dimension = routing.GetDimensionOrDie(count_dimension_name)

    print('create time dimension')
    # Add Time dimension for time windows, precedence constraints
    time_dimension_name = 'Time'
    routing.AddDimension(
        transit_callback_index, # same "cost" evaluator as above
        # args.horizon,  # slack for full range
        0, # try no slack
        args.horizon,  # max time is end of time horizon
        # True, # set to zero for each vehicle
        False,  # don't set time to zero...vehicles can wait at depot if necessary
        time_dimension_name)
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
    # this is new in v7.0, not sure what it does yet
    # time_dimension.SetGlobalSpanCostCoefficient(100)
    # turned it on and nothing worked, so leave off

    drive_dimension = None
    drive_dimension_name = 'Drive'
    print('create drive dimension')
    # Add Drive dimension for breaks logic
    print('creating drive callback for solver')
    drive_callback = partial(E.create_drive_callback(expanded_mm,
                                                     d),
                             manager)
    drive_callback_index = routing.RegisterTransitCallback(drive_callback)
    routing.AddDimension(
        drive_callback_index, # same "cost" evaluator as above
        0,  # No slack for drive dimension? infinite slack?
        args.horizon,  # max drive is end of drive horizon
        False, # set to zero for each vehicle
        drive_dimension_name)
    drive_dimension = routing.GetDimensionOrDie(drive_dimension_name)

    # constrain drive dimension to be drive_dimension_start_value at
    # start, so avoid negative numbers
    for vehicle in vehicles.vehicles:
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        routing.solver().Add(drive_dimension.CumulVar(index)==args.drive_dimension_start_value)


    demand_evaluator_index = routing.RegisterUnaryTransitCallback(
        partial(E.create_demand_callback(expanded_m.index,d), manager))

    print('create capacity dimension')
    # Add capacity dimension.  One load per vehicle
    cap_dimension_name = 'Capacity'
    vehicle_capacities = [veh.capacity for veh in vehicles.vehicles]
    routing.AddDimensionWithVehicleCapacity(
        demand_evaluator_index,
        0,  # null capacity slack
        vehicle_capacities,
        True,  # start cumul to zero
        cap_dimension_name)


    # [START pickup_delivery_constraint]
    print('apply pickup and delivery constraints')
    for idx in d.demand.index:
        record = d.demand.loc[idx]
        if not record.feasible:
            continue
        pickup_index = manager.NodeToIndex(record.origin)
        delivery_index = manager.NodeToIndex(record.destination)
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) ==
            routing.VehicleVar(delivery_index))
        routing.solver().Add(
            time_dimension.CumulVar(pickup_index) <=
            time_dimension.CumulVar(delivery_index))


    # [START time_window_constraint]
    print('apply time window  constraints')
    for idx in d.demand.index:
        record = d.demand.loc[idx]
        if not record.feasible:
            continue
        pickup_index = manager.NodeToIndex(record.origin)
        early = int(record.early)# 0
        late = int(record.late)  #  + args.horizon
        time_dimension.CumulVar(pickup_index).SetRange(early, late)
        routing.AddToAssignment(time_dimension.SlackVar(pickup_index))
        # and  add simulation-wide time windows (slack) for delivery nodes,
        dropoff_index = manager.NodeToIndex(record.destination)
        tt = expanded_mm.loc[record.origin,record.destination]
        if args.destination_time_windows:
            # early time windows is minimal breaks: start fresh, drive straight
            breaks = math.floor(tt/60/11) * 600
            early = int(record.early + tt + breaks)
            # late time window  maybe another break will have to be inserted
            breaks += 600
            late = int(record.late + tt + breaks)
            time_dimension.CumulVar(dropoff_index).SetRange(early, late)
        else:
            # just set dropoff time window same as 0, horizon
            early = 0
            late = args.horizon
            time_dimension.CumulVar(dropoff_index).SetRange(early, late)
        routing.AddToAssignment(time_dimension.SlackVar(dropoff_index))

    # now for all dummy nodes, set time windows
    # dummy nodes are identified by demand of zero
    for node in expanded_mm.index:
        # skip depot nodes---handled in vehicle time windows below
        if node == 0:
            continue
        # default is to give dummy nodes infinite time windows but
        # nodes leading to pickup nodes max out at pickup node time
        # window
        # optionally, don't do that for dummy nodes heading to pickups
        if d.get_demand(node) == 0:
            # this is a dummy node, not a pickup (1) not a dropoff (-1)

            index = manager.NodeToIndex(node)
            # set maximal time window
            tw = [0,args.horizon]
            #print(index,tw)
            # # dummy nodes can only get to one node
            # tt = expanded_mm.loc[node,:]
            # bool_idx = tt > 0
            # # next node is either origin, destination, or depot
            # next_node = expanded_mm.index[bool_idx].max()
            # # get next node time window to determine this node time window
            # tw = d.get_time_window(next_node)
            # if tw[0]>0 :
            #     # next node is a pickup, with early time > 0
            #     # but might be n breaks prior, so just zero it out
            #     tw = (0,tw[1])
            # # print('dummy node time window',node,index)
            time_dimension.CumulVar(index).SetRange(int(tw[0]),int(tw[1]))
            routing.AddToAssignment(time_dimension.SlackVar(index))

    # Add time window constraints for each vehicle start node
    # and 'copy' the slack var in the solution object (aka Assignment) to print it
    for vehicle in vehicles.vehicles:
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        # print('vehicle time window:',vehicle_id,index,vehicle.time_window)
        # not really needed unless different from 0, horizon
        time_dimension.CumulVar(index).SetRange(vehicle.time_window[0],
                                                vehicle.time_window[1])
        routing.AddToAssignment(time_dimension.SlackVar(index))


    # [START breaks logic]
    print('apply break rules')
    d.breaks_at_nodes_constraints(len(vehicles.vehicles),
                                  expanded_mm,
                                  manager,
                                  routing,
                                  time_dimension,
                                  count_dimension,
                                  drive_dimension,
                                  args.drive_dimension_start_value)

    print('breaks done')

    # # prevent impossible next nodes
    # print('remove impossible connections from solver')
    # for onode in expanded_mm.index:
    #     if onode % 100 == 0:
    #         print(onode,' of ',len(expanded_mm))
    #     o_idx = manager.NodeToIndex(onode)
    #     for dnode in expanded_mm.index:
    #         if onode == dnode:
    #             continue
    #         if np.isnan(expanded_mm.loc[onode,dnode]):
    #             # cannot connect, to prevent this combo
    #             d_idx = manager.NodeToIndex(dnode)
    #             if routing.NextVar(o_idx).Contains(d_idx):
    #                 # print('remove link from',onode,'to',dnode)
    #                 routing.NextVar(o_idx).RemoveValue(d_idx)
    # print('done with RemoveValue calls')


    # Setting first solution heuristic.
    # [START parameters]
    print('set up model parameters')
    # [START parameters]
    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)
        # routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        # routing_enums_pb2.FirstSolutionStrategy.ALL_UNPERFORMED)
        # routing_enums_pb2.FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION)

    # Disabling path Large Neighborhood Search is the default behaviour.  enable
    parameters.local_search_operators.use_path_lns = pywrapcp.BOOL_TRUE
    parameters.local_search_operators.use_inactive_lns = pywrapcp.BOOL_TRUE
    # Routing: forbids use of TSPOpt neighborhood,
    # parameters.local_search_operators.use_tsp_opt = pywrapcp.BOOL_FALSE
    # set a time limit
    parameters.time_limit.seconds = args.timelimit * 60   # timelimit minutes
    # sometimes helps with difficult solutions
    parameters.lns_time_limit.seconds = 10000  # 10000 milliseconds
    # i think this is the default
    # parameters.use_light_propagation = False
    # set to true to see the dump of search iterations
    parameters.log_search = pywrapcp.BOOL_TRUE

    # add disjunctions to deliveries to make it not fail
    penalty = 1000000000  # The cost for dropping a demand node from the plan.
    break_penalty = 1000000  # The cost for dropping a break node from the plan.
    # all nodes are droppable, so add disjunctions

    droppable_nodes = []
    for c in expanded_mm.index:
        if c == 0:
            # no disjunction on depot node
            continue
        p = penalty
        if d.get_demand(c) == 0:
            # no demand means break node
            p = break_penalty
        droppable_nodes.append(routing.AddDisjunction([manager.NodeToIndex(c)],
                                                      p))

    # can't pickle SwigPyObject... workaround?
    # print("Writing routing object out")
    # with open('routing.pkl', 'wb') as output:
    #     pickle.dump(routing,output,pickle.HIGHEST_PROTOCOL)
    #     # other stuff too?
    # print("Done Writing routing object to file routing.pkl")


    # set up initial routes
    trip_chains = IR.initial_routes(d,vehicles.vehicles,expanded_mm,
                                    manager,
                                    time_callback,
                                    drive_callback,
                                    debug = args.debug)

    initial_routes = [v for v in trip_chains.values()]
    #print(initial_routes)

    initial_solution = routing.ReadAssignmentFromRoutes(initial_routes,
                                                        True)

    # debug loop which is the bug?
    if not initial_solution:
        bug_route = []
        for route in initial_routes:
            single_solution = routing.ReadAssignmentFromRoutes([route],
                                                                True)
            if not single_solution:
                bug_route.append(route)
        for route in bug_route:
            for node in route:
                print(d.get_map_node(node))

    assert initial_solution
    print('Initial solution:')
    SO.print_initial_solution(d,expanded_m,expanded_mm,
                          vehicles,manager,routing,initial_solution,args.horizon)



    print('Calling the solver')
    # [START solve]

    assignment = routing.SolveFromAssignmentWithParameters(
        initial_solution, parameters)

    # [END solve]

    if assignment:
        ## save the assignment, (Google Protobuf format)
        #save_file_base = os.path.realpath(__file__).split('.')[0]
        #if routing.WriteAssignment(save_file_base + '_assignment.ass'):
        #    print('succesfully wrote assignment to file ' + save_file_base +
        #          '_assignment.ass')

        #print(expanded_mm)
        print('The Objective Value is {0}'.format(assignment.ObjectiveValue()))
        print('details:')
        SO.print_solution(d,expanded_m,expanded_mm,
                          vehicles,manager,routing,assignment,args.horizon)

        SO.csv_output(d,expanded_m,expanded_mm,
                      vehicles,manager,routing,assignment,args.horizon,
                      args.vehicle_output)
        SO.csv_demand_output(d,expanded_m,expanded_mm,
                             vehicles,manager,routing,assignment,args.horizon,
                             args.demand_output)

    else:
        print('assignment failed')



if __name__ == '__main__':
    main()
