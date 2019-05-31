from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
from functools import partial
import evaluators as E

def use_nodes(record,d):
    nodes = [0,record.origin,record.destination]
    nodes.extend(d.get_break_node_chain(0,record.origin))
    nodes.extend(d.get_break_node_chain(record.origin,record.destination))
    nodes.extend(d.get_break_node_chain(record.destination,0))
    return nodes

# def small_run(record,time_matrix,d,horizon,base_value,vehicle_capacity=1):
#     print('solving for',nodes)
#     num_nodes = len(nodes)
#     mini_manager = pywrapcp.RoutingIndexManager(
#         num_nodes, # just this demand
#         1, # one vehicle
#         0) # depot is zero
#     time_dimension_name = 'time'
#     drive_dimension_name = 'drive'
#     short_break_dimension_name = 'break'
#     cap_dimension_name = 'cap'


#     pickup_index = mini_manager.NodeToIndex(1)
#     dropoff_index = mini_manager.NodeToIndex(2)

#     # Create Routing Model.
#     mini_routing = pywrapcp.RoutingModel(mini_manager)
#     time_callback = E.create_time_callback3(time_matrix, nodes, d)

#     transit_callback_index2 = mini_routing.RegisterTransitCallback(partial(time_callback,
#                                                                            mini_manager))
#     mini_routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index2)


#     mini_routing.AddDimension(
#         transit_callback_index2, # same "cost" evaluator as above
#         0, # try no slack
#         horizon,  # max time is end of time horizon
#         # True, # set to zero for each vehicle
#         False,  # don't set time to zero...vehicles can wait at depot if necessary
#         time_dimension_name)

#     time_dimension2 = mini_routing.GetDimensionOrDie(time_dimension_name)

#     drive_callback2 = partial(E.create_drive_callback3(time_matrix,
#                                                        nodes,
#                                                        d,
#                                                        11*60,
#                                                        10*60),
#                               mini_manager)
#     drive_callback_index2 = mini_routing.RegisterTransitCallback(drive_callback2)
#     mini_routing.AddDimension(
#         drive_callback_index2, # same "cost" evaluator as above
#         0,  # No slack for drive dimension? infinite slack?
#         horizon,  # max drive is end of drive horizon
#         False, # set to zero for each vehicle
#         drive_dimension_name)

#     drive_dimension2 = mini_routing.GetDimensionOrDie(drive_dimension_name)
#     # constrain drive dimension to be drive_dimension_start_value at
#     # start, so avoid negative numbers

#     vehicle_id = 0
#     index = mini_routing.Start(vehicle_id)
#     mini_routing.solver().Add(drive_dimension2.CumulVar(index)==base_value)

#     # Add short_Break dimension for breaks logic
#     short_break_callback2 = partial(E.create_short_break_callback3(time_matrix,
#                                                                    nodes,
#                                                                    d,
#                                                                    8*60,
#                                                                    30),
#                                     mini_manager)

#     short_break_callback_index2 = mini_routing.RegisterTransitCallback(short_break_callback2)
#     mini_routing.AddDimension(
#         short_break_callback_index2, # modified "cost" evaluator as above
#         0,  # No slack
#         horizon,  # max horizon is horizon
#         False, # set to zero for each vehicle
#         short_break_dimension_name)
#     short_break_dimension2 = mini_routing.GetDimensionOrDie(short_break_dimension_name)
#     # constrain short_break dimension to be drive_dimension_start_value at
#     # start, so avoid negative numbers
#     mini_routing.solver().Add(short_break_dimension2.CumulVar(index)==base_value)


#     demand_evaluator_index = mini_routing.RegisterUnaryTransitCallback(
#         partial(E.create_demand_callback(nodes,d), mini_manager))


#     vehicle_capacities = [vehicle_capacity]
#     mini_routing.AddDimensionWithVehicleCapacity(
#         demand_evaluator_index,
#         0,  # null capacity slack
#         vehicle_capacities,
#         True,  # start cumul to zero
#         cap_dimension_name)

#     # print('apply pickup and delivery constraints')

#     pickup_index = mini_manager.NodeToIndex(record.origin)
#     delivery_index = mini_manager.NodeToIndex(record.destination)
#     mini_routing.AddPickupAndDelivery(pickup_index, delivery_index)
#     mini_routing.solver().Add(
#         mini_routing.VehicleVar(pickup_index) ==
#         mini_routing.VehicleVar(delivery_index))
#     mini_routing.solver().Add(
#             time_dimension2.CumulVar(pickup_index) <=
#             time_dimension2.CumulVar(delivery_index))

#     early = int(record.early)# 0
#     late = int(record.late)  #  + horizon
#     time_dimension2.CumulVar(pickup_index).SetRange(early, late)
#     # just set dropoff time window same as 0, horizon
#     early = late
#     late = horizon
#     time_dimension2.CumulVar(dropoff_index).SetRange(early, late)
#     for node_idx in range(0,len(nodes)):
#         node = nodes[node_idx]
#         if d.get_demand(node) == 0:
#             # do the same for both depot and dummy nodes
#             index = mini_manager.NodeToIndex(node_idx)
#             # print(index)
#             time_dimension2.CumulVar(index).SetRange(0,int(horizon))

#     d.break_constraint(1,2,
#                        mini_manager,
#                        mini_routing,
#                        drive_dimension2,
#                        short_break_dimension2,
#                        base_value)

#     index = mini_routing.End(0)
#     end_drive = drive_dimension2.CumulVar(index)
#     end_short = short_break_dimension2.CumulVar(index)
#     solver = mini_routing.solver()
#     solver.AddConstraint(
#         end_drive >= base_value)
#     solver.AddConstraint(
#         end_drive < base_value+(11*60))
#     solver.AddConstraint(
#         end_short >= base_value)
#     solver.AddConstraint(
#         end_short < base_value+(8*60))

#     parameters2 = pywrapcp.DefaultRoutingSearchParameters()
#     parameters2.first_solution_strategy = (
#         routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)
#     parameters2.local_search_operators.use_path_lns = pywrapcp.BOOL_TRUE
#     parameters2.local_search_operators.use_inactive_lns = pywrapcp.BOOL_TRUE
#     parameters2.time_limit.seconds = 60   # 1 minute
#     parameters2.lns_time_limit.seconds = 10000  # 10000 milliseconds
#     parameters2.log_search = pywrapcp.BOOL_TRUE

#     # add disjunctions to deliveries to make it not fail
#     penalty = 1000000000  # The cost for dropping a demand node from the plan.
#     for c in range(0,len(nodes)):
#         if c > 0:
#             # no disjunction on depot node
#             mini_routing.AddDisjunction([mini_manager.NodeToIndex(c)],
#                                         penalty)
#     assignment = mini_routing.SolveWithParameters(parameters2)

#     assert assignment
#     index = mini_routing.Start(0)
#     initial_route = []
#     while not mini_routing.IsEnd(index):
#         if index != mini_routing.Start(0):
#             node_idx = mini_manager.IndexToNode(index)
#             initial_route.append(nodes[node_idx])
#         index = assignment.Value(mini_routing.NextVar(index))
#     return initial_route

def get_route(v,assignment,routing,manager):
    index = routing.Start(v)
    initial_route = []
    while not routing.IsEnd(index):
        if index != routing.Start(v):
            node_idx = manager.IndexToNode(index)
            initial_route.append(node_idx)
        index = assignment.Value(routing.NextVar(index))
    return initial_route

def setup_params(timelimit):
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
    parameters.time_limit.seconds =  timelimit * 60  # timelimit minutes
    # sometimes helps with difficult solutions
    parameters.lns_time_limit.seconds = 10000  # 10000 milliseconds
    # i think this is the default
    # parameters.use_light_propagation = False
    # set to true to see the dump of search iterations
    parameters.log_search = pywrapcp.BOOL_TRUE
    return parameters

def model_run(d,t,v,base_value,demand_subset=None,initial_routes=None,timelimit=1):

    # use demand_subset to pick out a subset of nodes
    if demand_subset != None:
        t = t.copy()
        l = len(t.index)
        index_mask = t.index.isin(demand_subset).reshape(l,1)
        column_mask = t.columns.isin(demand_subset)
        m = np.multiply(index_mask,column_mask)
        t = t.where(m)
    else:
        demand_subset = t.index

    time_dimension_name = 'time'
    drive_dimension_name = 'drive'
    short_break_dimension_name = 'break'
    cap_dimension_name = 'cap'
    count_dimension_name = 'count'

    num_nodes = len(t.index)
    manager = pywrapcp.RoutingIndexManager(
        num_nodes,
        len(v),
        v[0].depot_index)
    routing = pywrapcp.RoutingModel(manager)

    time_callback = partial(E.create_time_callback2(t, d), manager)
    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    routing.AddConstantDimension(
        1, # increment by one every time
        num_nodes,  # max count is visit all the nodes
        True,  # set count to zero
        count_dimension_name)
    count_dimension = routing.GetDimensionOrDie(count_dimension_name)

    routing.AddDimension(
        transit_callback_index, # same "cost" evaluator as above
        0, # try no slack
        d.horizon,  # max time is end of time horizon
        False,  # don't set time to zero...vehicles can wait at depot if necessary
        time_dimension_name)
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
    # time_dimension.SetGlobalSpanCostCoefficient(100)

    drive_callback = partial(E.create_drive_callback(t, d, 11*60, 10*60), manager)
    drive_callback_index = routing.RegisterTransitCallback(drive_callback)
    routing.AddDimension(
        drive_callback_index, # same "cost" evaluator as above
        0,  # No slack for drive dimension? infinite slack?
        d.horizon,  # max drive is end of drive horizon
        False, # set to zero for each vehicle
        drive_dimension_name)
    drive_dimension = routing.GetDimensionOrDie(drive_dimension_name)

    short_break_callback = partial(E.create_short_break_callback(t, d, 8*60, 30), manager)
    short_break_callback_index = routing.RegisterTransitCallback(short_break_callback)
    routing.AddDimension(
        short_break_callback_index, # modified "cost" evaluator as above
        0,  # No slack
        d.horizon,  # max horizon is horizon
        False, # set to zero for each vehicle
        short_break_dimension_name)
    short_break_dimension = routing.GetDimensionOrDie(short_break_dimension_name)


    demand_evaluator_index = routing.RegisterUnaryTransitCallback(
        partial(E.create_demand_callback(t.index,d), manager))
    vehicle_capacities = [veh.capacity for veh in v]
    routing.AddDimensionWithVehicleCapacity(
        demand_evaluator_index,
        0,  # null capacity slack
        vehicle_capacities,
        True,  # start cumul to zero
        cap_dimension_name)

    for idx in d.demand.index:
        record = d.demand.loc[idx]
        if not record.feasible:
            continue
        if np.isnan(t.loc[record.origin,record.destination]):
            # also catches case of demand pair not in demand subset
            continue
        pickup_index = manager.NodeToIndex(record.origin)
        delivery_index = manager.NodeToIndex(record.destination)
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index))
        routing.solver().Add(
            time_dimension.CumulVar(pickup_index) <= time_dimension.CumulVar(delivery_index))
        # [START time_window_constraint]
        early = int(record.early)
        late = int(record.late)
        time_dimension.CumulVar(pickup_index).SetRange(early, late)
        routing.AddToAssignment(time_dimension.SlackVar(pickup_index))
        # and  add simulation-wide time windows (slack) for delivery nodes,
        dropoff_index = manager.NodeToIndex(record.destination)
        # tt = t.loc[record.origin,record.destination]
        # just set dropoff time window same as 0, horizon
        early = 0
        late = d.horizon
        time_dimension.CumulVar(dropoff_index).SetRange(early, late)
        routing.AddToAssignment(time_dimension.SlackVar(dropoff_index))

    for node in demand_subset:
        # skip depot nodes---handled in vehicle time windows
        if node == 0:
            continue
        # also skip nodes with non zero demand (handled above)
        if d.get_demand(node) != 0:
            continue

        # this is a dummy node, not a pickup (demand = 1) not a dropoff (-1)
        index = manager.NodeToIndex(node)
        # set maximal time window
        time_dimension.CumulVar(index).SetRange(0,d.horizon)
        routing.AddToAssignment(time_dimension.SlackVar(index))

    # vehicle constraints, time windows etc
    # constrain long break and short_break dimensions to be base_value at
    # start, so avoid negative numbers
    for vehicle in v:
        index = routing.Start(vehicle.index)
        routing.solver().Add(drive_dimension.CumulVar(index)==base_value)
        routing.solver().Add(short_break_dimension.CumulVar(index)==base_value)
        time_dimension.CumulVar(index).SetRange(vehicle.time_window[0],
                                                vehicle.time_window[1])
        routing.AddToAssignment(time_dimension.SlackVar(index))



    d.breaks_at_nodes_constraints(len(v),
                                  t,
                                  manager,
                                  routing,
                                  time_dimension,
                                  count_dimension,
                                  drive_dimension,
                                  short_break_dimension,
                                  base_value)

    parameters = setup_params(timelimit)
    # add disjunctions to deliveries to make it not fail
    penalty = 1000000000  # The cost for dropping a demand node from the plan.
    break_penalty = 0  # The cost for dropping a break node from the plan.
    # all nodes are droppable, so add disjunctions

    droppable_nodes = [routing.AddDisjunction([manager.NodeToIndex(c)],
                                              penalty) for c in d.get_node_list()]
    breaknodes = np.setdiff1d(t.index,d.equivalence.index)
    # get rid of depot node
    breaknodes = np.delete(breaknodes,0)

    more_droppables = [routing.AddDisjunction([manager.NodeToIndex(c)],
                                              break_penalty) for c in breaknodes]
    assignment = None
    if initial_routes:
        routing.CloseModelWithParameters(parameters)
        initial_solution = routing.ReadAssignmentFromRoutes(initial_routes,
                                                            True)
        assert initial_solution
        assignment = routing.SolveFromAssignmentWithParameters(
            initial_solution, parameters)
    else:
        assignment = routing.SolveWithParameters(parameters)
    assert assignment
    return (assignment,routing,manager)

def model_run_nobreaks(d,t,v,demand_subset=None,initial_routes=None,timelimit=1):

    # use demand_subset to pick out a subset of nodes
    if demand_subset != None:
        t = t.copy()
        l = len(t.index)
        index_mask = t.index.isin(demand_subset).reshape(l,1)
        column_mask = t.columns.isin(demand_subset)
        m = np.multiply(index_mask,column_mask)
        t = t.where(m)
    else:
        demand_subset = t.index

    time_dimension_name = 'time'
    cap_dimension_name = 'cap'
    count_dimension_name = 'count'

    num_nodes = len(t.index)
    manager = pywrapcp.RoutingIndexManager(
        num_nodes,
        len(v),
        v[0].depot_index)
    routing = pywrapcp.RoutingModel(manager)

    time_callback = E.create_time_callback2(t, d)
    demand_callback = E.create_demand_callback(t.index,d)

    transit_callback_index = routing.RegisterTransitCallback(
        partial(time_callback, manager)
    )

    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # count
    routing.AddConstantDimension(
        1, # increment by one every time
        num_nodes,  # max count is visit all the nodes
        True,  # set count to zero
        count_dimension_name)
    count_dimension = routing.GetDimensionOrDie(count_dimension_name)

    # time
    routing.AddDimension(
        transit_callback_index, # same "cost" evaluator as above
        0, # try no slack
        d.horizon,  # max time is end of time horizon
        False,  # don't set time to zero...vehicles can wait at depot if necessary
        time_dimension_name)
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
    # time_dimension.SetGlobalSpanCostCoefficient(100)

    # capacity/demand
    demand_evaluator_index = routing.RegisterUnaryTransitCallback(
        partial(demand_callback, manager))
    vehicle_capacities = [veh.capacity for veh in v]
    routing.AddDimensionWithVehicleCapacity(
        demand_evaluator_index,
        0,  # null capacity slack
        vehicle_capacities,
        True,  # start cumul to zero
        cap_dimension_name)

    # P&D, time window
    for idx in d.demand.index:
        record = d.demand.loc[idx]
        # print('origin to dest',record.origin,record.destination)

        if not record.feasible:
            continue
        if np.isnan(t.loc[record.origin,record.destination]):
            # print('origin to dest is nan',record.origin,record.destination,
            #      t.loc[record.origin,record.destination])
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
        early = int(record.early)
        late = int(record.late)
        time_dimension.CumulVar(pickup_index).SetRange(early, late)
        routing.AddToAssignment(time_dimension.SlackVar(pickup_index))
        # and  add simulation-wide time windows (slack) for delivery nodes,
        dropoff_index = manager.NodeToIndex(record.destination)
        tt = t.loc[record.origin,record.destination]
        # just set dropoff time window same as 0, horizon
        early = 0
        late = d.horizon
        time_dimension.CumulVar(dropoff_index).SetRange(early, late)
        routing.AddToAssignment(time_dimension.SlackVar(dropoff_index))

    for vehicle in v:
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        # print('vehicle time window:',vehicle_id,index,vehicle.time_window)
        # not really needed unless different from 0, horizon
        time_dimension.CumulVar(index).SetRange(vehicle.time_window[0],
                                                vehicle.time_window[1])
        routing.AddToAssignment(time_dimension.SlackVar(index))


    parameters = setup_params(timelimit)

    # add disjunctions to deliveries to make it not fail
    penalty = 10000000  # The cost for dropping a demand node from the plan.
    # all nodes are droppable, so add disjunctions

    droppable_nodes = [routing.AddDisjunction([manager.NodeToIndex(c)],
                                              penalty) for c in d.get_node_list()]
    assignment = None
    if initial_routes:
        routing.CloseModelWithParameters(parameters)
        initial_solution = routing.ReadAssignmentFromRoutes(initial_routes,
                                                            True)
        assert initial_solution
        assignment = routing.SolveFromAssignmentWithParameters(
            initial_solution, parameters)
    else:
        assignment = routing.SolveWithParameters(parameters)
    assert assignment
    return (assignment,routing,manager)
