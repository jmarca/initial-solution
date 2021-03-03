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


# globals.  does python do this?
time_dimension_name = 'time'
cap_dimension_name = 'cap'
count_dimension_name = 'count'
drive_dimension_name = 'drive'
short_break_dimension_name = 'break'



def get_route(v,assignment,routing,manager):
    index = routing.Start(v)
    initial_route = []
    while not routing.IsEnd(index):
        if index != routing.Start(v):
            node_idx = manager.IndexToNode(index)
            initial_route.append(node_idx)
        index = assignment.Value(routing.NextVar(index))
    return initial_route

def setup_params(args):
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
    if args is not None:
        parameters.time_limit.seconds = args.timelimit * 60  # timelimit minutes
        if args.guided_local:
            print('including guided local search')
            parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    else:
        parameters.time_limit.seconds = 60
    # sometimes helps with difficult solutions
    parameters.lns_time_limit.seconds = 10000  # 10000 milliseconds
    # i think this is the default
    # parameters.use_light_propagation = False
    # set to true to see the dump of search iterations
    parameters.log_search = pywrapcp.BOOL_TRUE

    return parameters

def unset_times(t,demand_subset):
    t = t.copy()
    l = len(t.index)
    index_mask = t.index.isin(demand_subset).reshape(l,1)
    column_mask = t.columns.isin(demand_subset)
    m = np.multiply(index_mask,column_mask)
    return t.where(m)



def breaks_at_nodes_constraints(d,
                                v,
                                time_matrix,
                                manager,
                                routing,
                                base_value):

    solver = routing.solver()
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
    drive_dimension = routing.GetDimensionOrDie(drive_dimension_name)
    short_break_dimension = routing.GetDimensionOrDie(short_break_dimension_name)
    count_dimension = routing.GetDimensionOrDie(count_dimension_name)

    feasible_index = d.demand.feasible
    for idx in d.demand.index[feasible_index]:
        record = d.demand.loc[idx,:]
        # double check that is possible (in case just solving a limited set
        if np.isnan(time_matrix.loc[record.origin,record.destination]):
            continue
        d.break_constraint(record.origin,record.destination,
                           manager,routing,
                           drive_dimension,
                           short_break_dimension,
                           base_value
        )

    # constraints on return to depot, otherwise we just collect
    # break nodes on the way back and go deeply negative
    for veh in v:
        index = routing.End(veh.index)
        end_drive = drive_dimension.CumulVar(index)
        end_short = short_break_dimension.CumulVar(index)
        solver.AddConstraint(
            end_drive >= base_value)
        solver.AddConstraint(
            end_drive < base_value+(11*60))

        solver.AddConstraint(
            end_short >= base_value)

        solver.AddConstraint(
            end_short < base_value+(8*60))

def setup_model(d,t,v):
    # common to both with and without breaks
    num_nodes = len(t.index)
    manager = pywrapcp.RoutingIndexManager(
        num_nodes,
        len(v),
        v[0].depot_index)

    model_parameters = pywrapcp.DefaultRoutingModelParameters()
    model_parameters.max_callback_cache_size = 2 * num_nodes * num_nodes
    routing = pywrapcp.RoutingModel(manager, model_parameters)

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
        # d.horizon,  # try infinite slack
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
    cap_dimension = routing.GetDimensionOrDie(cap_dimension_name)

    return (num_nodes,manager,routing)

def break_nodes_time_windows(d,demand_subset,manager,routing):
    # Pickup & Delivery, plus time window
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
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


def pick_deliver_constraints(d,t,manager,routing):
    # Pickup & Delivery, plus time window
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
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
        # tt = t.loc[record.origin,record.destination]
        # just set dropoff time window same as 0, horizon
        early = 0
        late = d.horizon
        time_dimension.CumulVar(dropoff_index).SetRange(early, late)
        routing.AddToAssignment(time_dimension.SlackVar(dropoff_index))

def vehicle_time_constraints(v,manager,routing):
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
    for vehicle in v:
        index = routing.Start(vehicle.index)
        time_dimension.CumulVar(index).SetRange(vehicle.time_window[0],
                                                vehicle.time_window[1])
        routing.AddToAssignment(time_dimension.SlackVar(index))

def vehicle_time_drive_constraints(v,base_value,manager,routing):
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
    short_break_dimension = routing.GetDimensionOrDie(short_break_dimension_name)
    drive_dimension = routing.GetDimensionOrDie(drive_dimension_name)
    for vehicle in v:
        index = routing.Start(vehicle.index)
        routing.solver().Add(drive_dimension.CumulVar(index)==base_value)
        routing.solver().Add(short_break_dimension.CumulVar(index)==base_value)
        time_dimension.CumulVar(index).SetRange(vehicle.time_window[0],
                                                vehicle.time_window[1])
        routing.AddToAssignment(time_dimension.SlackVar(index))



def model_run(d,t,v,base_value,
              demand_subset=None,
              initial_routes=None,
              args=None):

    # use demand_subset to pick out a subset of nodes
    if demand_subset != None:
        t = unset_times(t,demand_subset)
    else:
        demand_subset = t.index

    (num_nodes,manager,routing) = setup_model(d,t,v)

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

    pick_deliver_constraints(d,t,manager,routing)
    break_nodes_time_windows(d,demand_subset,manager,routing)


    # vehicle constraints, time windows etc
    # constrain long break and short_break dimensions to be base_value at
    # start, so avoid negative numbers
    vehicle_time_drive_constraints(v,base_value,manager,routing)


    breaks_at_nodes_constraints(d, v, t,
                                manager,
                                routing,
                                base_value)

    parameters = setup_params(args)
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
    assignment = run_solver(routing,parameters,initial_routes)
    return (assignment,routing,manager)

def run_solver(routing,parameters,initial_routes):
    if initial_routes:
        routing.CloseModelWithParameters(parameters)
        initial_solution = routing.ReadAssignmentFromRoutes(initial_routes,
                                                            True)
        assert initial_solution
        return routing.SolveFromAssignmentWithParameters(initial_solution, parameters)
    else:
        return routing.SolveWithParameters(parameters)



def model_run_nobreaks(d,t,v,demand_subset=None,initial_routes=None,args=None):

    # use demand_subset to pick out a subset of nodes
    if demand_subset != None:
        t = unset_times(t,demand_subset)
    else:
        demand_subset = t.index


    (num_nodes,manager,routing) = setup_model(d,t,v)

    pick_deliver_constraints(d,t,manager,routing)
    vehicle_time_constraints(v,manager,routing)

    parameters = setup_params(args)

    # add disjunctions to deliveries to make it not fail
    penalty = 10000000  # The cost for dropping a demand node from the plan.
    # all nodes are droppable, so add disjunctions

    droppable_nodes = [routing.AddDisjunction([manager.NodeToIndex(c)],
                                              penalty) for c in d.get_node_list()]
    assignment = run_solver(routing,parameters,initial_routes)
    return (assignment,routing,manager)
