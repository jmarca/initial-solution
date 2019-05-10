# create simple 2D array for distance lookup?
# Define cost of each arc.
import numpy as np
import sys
import pandas as pd

def create_demand_callback(node_list,demand):
    """ create a callback function for demand """
    _demand = {}
    for node in node_list:
        _demand[node] = demand.get_demand(node)
    print('size of demand matrix is ',len(_demand))
    def demand_callback(manager, index):
        """Returns the demand at the index, if defined, or zero."""
        # Convert from routing variable Index to demand array Node.
        node = manager.IndexToNode(index)
        # print(node)
        # print(_demand[node])
        return _demand[node]


    # return the callback, which will need to be set up with partial
    return demand_callback


def create_time_callback(travel_minutes_matrix,
                         demand):
    """create a callback function for time.  presumes that
       travel_minutes_matrix is in solver space, not map space (has
       been passed through demand.generate_solver_space_matrix

    """
    # time matrix is now in model space, not map space
    # preprocess travel and service time to speed up solver
    _total_time = {}
    max_time = travel_minutes_matrix.max().max()
    penalty_time =  int(10000000 * max_time)
    # penalty_time =  int(9223372036854775808)
    # penalty_time = int(100 * max_time)
    print ('using a maximum time for forbidden links of ',penalty_time)

    # nodes are in travel time matrix
    node_list = [n for n in travel_minutes_matrix.index]
    # print('len node list is ',len(node_list))
    for from_node in node_list:
        if from_node % 100 == 0:
            print(from_node,' of ',len(travel_minutes_matrix.index))
        _total_time[from_node] = {}
        # mapnode_from = demand.get_map_node(from_node)
        service_time = demand.get_service_time(from_node)
        for to_node in node_list:
            if from_node == to_node:
                _total_time[from_node][to_node] = 0
            else:
                # mapnode_to = demand.get_map_node(to_node)
                if not np.isnan(travel_minutes_matrix.loc[from_node,to_node]) :
                    _total_time[from_node][to_node] = int(
                        travel_minutes_matrix.loc[from_node,to_node]
                        + service_time
                    )
                else:
                    _total_time[from_node][to_node] = penalty_time
                # print(from_node,to_node,mapnode_from,mapnode_to,_total_time[from_node][to_node])

    def time_callback(manager, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # print(from_node,to_node)
        # print(_total_time[from_node][to_node])
        return _total_time[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return time_callback

def create_dist_callback(dist_matrix,
                         demand):
    """ create a callback function for dist """
    # dist matrix is now in model space, not map space
    # preprocess travel and service dist to speed up solver
    _total_dist = {}
    # can get node list from dist matrix now
    node_list = [ n for n in dist_matrix.index ]
    for from_node in node_list:
        _total_dist[from_node] = {}
        # no longer need to get map node, as distance matrix is in solver node space
        # mapnode_from = demand.get_map_node(from_node)

        for to_node in node_list:
            if from_node == to_node:
                _total_dist[from_node][to_node] = 0
            else:
                # mapnode_to = demand.get_map_node(to_node)
                if not np.isnan(dist_matrix.loc[from_node,to_node]) :
                    _total_dist[from_node][to_node] = int(
                        dist_matrix.loc[from_node,to_node]
                    )
                else:
                    _total_dist[from_node][to_node] = sys.maxsize


    def dist_callback(manager, from_index, to_index):
        """Returns the travel dist between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # calling pandas object might break C++, so switched to
        return _total_dist[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return dist_callback


def create_time_callback2(travel_minutes_matrix,
                          demand):
    """Time callback version 2

       Use this one if breaks happen at nodes.  The difference with
       create_time_callback is that break nodes here (those with zero
       demand, etc) have a service time of 11 hours, to simulate
       taking the break.

    """
    # time matrix is now in model space, not map space
    # preprocess travel and service time to speed up solver
    _total_time = {}
    max_time = travel_minutes_matrix.max().max()
    penalty_time =  int(10000000 * max_time)
    # nodes are in travel time matrix
    node_list = [n for n in travel_minutes_matrix.index]
    # print('len node list is ',len(node_list))
    for from_node in node_list:
        if from_node % 100 == 0:
            print(from_node,' of ',len(travel_minutes_matrix.index))
        _total_time[from_node] = {}
        truck_service_time = demand.get_service_time(from_node)
        service_time = truck_service_time
        if from_node > 0 and truck_service_time == 0:
            # this is a break node, so bump up the service time
            service_time = 60*10 # FIXME need to also do 30 minute breaks
                                 # probably set up a class for nodes
                                 # have a class
                                 # FIXME use the break node class here
        for to_node in node_list:
            if from_node == to_node:
                _total_time[from_node][to_node] = 0
            else:
                # mapnode_to = demand.get_map_node(to_node)
                if not np.isnan(travel_minutes_matrix.loc[from_node,to_node]) :
                    _total_time[from_node][to_node] = int(
                        travel_minutes_matrix.loc[from_node,to_node]
                        + service_time
                    )
                else:
                    _total_time[from_node][to_node] = penalty_time
    # print(travel_minutes_matrix)
    # print (pd.DataFrame.from_dict(_total_time,orient='index'))

    def time_callback(manager, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # print('time',from_node,to_node,_total_time[from_node][to_node])
        return _total_time[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return time_callback


def create_drive_callback(travel_minutes_matrix,
                          demand):
    """create a callback function for drivetime.  presumes that
       travel_minutes_matrix is in solver space, not map space (has
       been passed through demand.generate_solver_space_matrix.  Also,
       create negative demands (unload drive time) at break nodes, but
       only visit break nodes if need to do so.

    """
    # time matrix is now in model space, not map space
    # preprocess travel and service time to speed up solver
    _total_time = {}
    max_time = travel_minutes_matrix.max().max()
    penalty_time =  int(10000000 * max_time)
    # nodes are in travel time matrix
    node_list = [n for n in travel_minutes_matrix.index]
    # print('len node list is ',len(node_list))
    for from_node in node_list:
        # don't care about type of origin node
        if from_node % 100 == 0:
            print(from_node,' of ',len(travel_minutes_matrix.index))
        _total_time[from_node] = {}
        for to_node in node_list:
            if from_node == to_node:
                _total_time[from_node][to_node] = 0
            else:
                tt = travel_minutes_matrix.loc[from_node,to_node]
                if not np.isnan(tt) :
                    # ascertain the type of node
                    service_time = 0
                    if to_node > 0 and demand.get_demand(to_node) == 0:
                        # this is a break node, so account for rest time
                        bn = demand.get_break_node(to_node)
                        service_time = int(bn.drive_time_restore())

                    _total_time[from_node][to_node] = int(
                        service_time + tt
                    )
                else:
                    _total_time[from_node][to_node] = penalty_time
    print('drive time')
    print (pd.DataFrame.from_dict(_total_time,orient='index'))
    # assert 0

    def time_callback(manager, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # print('drive time',from_node,to_node,_total_time[from_node][to_node])
        return _total_time[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return time_callback
