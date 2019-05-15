# create simple 2D array for distance lookup?
# Define cost of each arc.
import numpy as np
import sys
import os
import pandas as pd
from multiprocessing import Pool
import itertools as iter

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
    # preprocess travel and service time to speed up solver

    number = len(travel_minutes_matrix)
    max_time = travel_minutes_matrix.max().max()
    penalty_time =  int(10000000 * max_time)
    # penalty_time =  int(9223372036854775808)
    # penalty_time = int(100 * max_time)
    print ('using a maximum time for forbidden links of ',penalty_time)
    _total_time = penalty_time * np.ones(number,number)
    def g(from_node,to_node):
        if from_node == to_node:
            _total_time[from_node][to_node] = 0
        else:
            service_time = demand.get_service_time(from_node)
            if not np.isnan(travel_minutes_matrix.loc[from_node,to_node]) :
                _total_time[from_node,to_node] = int(
                    travel_minutes_matrix.loc[from_node,to_node]
                    + service_time
                )
            # redundant
            # else:
            #     _total_time[from_node,to_node] = penalty_time

    ncpus = len(os.sched_getaffinity(0))
    p = Pool(ncpus)

    # nodes are in travel time matrix
    node_list = [n for n in travel_minutes_matrix.index]

    travel_times = p.map(g,iter.permutations(node_list,2))
    # print(travel_times)
    assert 0
    # print('len node list is ',len(node_list))

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

def g(pair):
    (a,b) = pair
    (from_node,from_demand,from_service) = a
    (to_node,to_demand,to_service) = b
    value = to_service
    if from_node == to_node:
        value = 0
    return [from_node,to_node,value]

def f(pair):
    (a,b) = pair
    (from_node,from_demand,from_service) = a
    (to_node,to_demand,to_service) = b
    value = from_service
    if from_node == to_node:
        value = 0
    return [from_node,to_node,value]

# this one is for short breaks.
# short breaks cannot get two 8hr restores in a row
def e(pair):
    (a,b) = pair
    (from_node,from_demand,from_service) = a
    (to_node,to_demand,to_service) = b
    if from_node in [0,3,4] and to_node in [0,3,4]:
        print(a,b)
    value = from_service
    if value < -480:
        value = -480
    if from_node == to_node:
        value = 0
    # FIXME this is a quick and dirty hack
    if value < 0 and from_service == -480 and  to_service == -660:
        value = -3*60 # 11 hrs minus 8 hrs.  Don't want to get greedy
    return [from_node,to_node,value]

# this function works to set up impact of any node on total time
# breaks add break_time to cumulative time
# pickup and delivery nodes add service time to cumulative time
# depot nodes add nothing
def make_location_data(pair):
    (node,demand) = pair
    service_time = demand.get_service_time(node)
    d = demand.get_demand(node)
    break_node = demand.get_break_node(node)
    if break_node != None:
        service_time = break_node.break_time
    return (node,d,service_time)

# this function works to set up impact of a break node on the drive time dimensions
# The 11 hr rule resets both the 30 minute break and the 10 hr break
# The 8hr rule resets just the 30 minute break
# so the if statement filters out any impact the 30 min break might have on the
# 11 hr rule counter
def make_drive_data(pair):
    (node,demand,period,break_time) = pair
    service_time = 0
    d = demand.get_demand(node)
    break_node = demand.get_break_node(node)
    if break_node != None:
        # duck typing of a sorts
        if break_node.break_time >= break_time and abs(break_node.drive_time_restore())>=period:
            # quacks like the duck we're looking for
            service_time = break_node.drive_time_restore()
    return (node,d,service_time)


def create_time_callback2(travel_minutes_matrix,
                          demand):
    """Time callback version 2

       Use this one if breaks happen at nodes.  The difference with
       create_time_callback is that break nodes here (those with zero
       demand, etc) have a service time of 11 hours, to simulate
       taking the break.

    """
    # preprocess travel and service time to speed up solver
    number = len(travel_minutes_matrix)
    max_time = travel_minutes_matrix.max().max()
    penalty_time =  int(10000000 * max_time)

    _total_time = penalty_time * np.ones((number,number))

    node_list = [(n,demand) for n in travel_minutes_matrix.index]
    # print('len node list is ',len(node_list))
    ncpus = len(os.sched_getaffinity(0))
    p = Pool(ncpus)
    node_demand_service_list = p.map(make_location_data,node_list)
    # print(node_demand_service_list)

    travel_times = p.map(f,iter.product(node_demand_service_list,repeat=2))
    df_stacked_service_time = pd.DataFrame(travel_times,columns=['from','to','service_time'])
    # print(df_stacked_service_time)
    df_service_time = df_stacked_service_time.pivot(index='from',columns='to',values='service_time')

    _total_time = (df_service_time + travel_minutes_matrix).fillna(penalty_time).values
    # print(df_service_time)
    # print(travel_minutes_matrix.loc[:,[0,1,5,15,16,17,18]])
    # print(df_service_time + travel_minutes_matrix)
    # print (pd.DataFrame.from_dict(_total_time,orient='index'))

    def time_callback(manager, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        #print('time',from_node,to_node,_total_time[from_node,to_node])
        return _total_time[from_node,to_node]

    # return the callback, which will need to be set up with partial
    return time_callback


def create_drive_callback(travel_minutes_matrix,
                          demand,
                          period,
                          break_time):
    """create a callback function for drivetime.  presumes that
       travel_minutes_matrix is in solver space, not map space (has
       been passed through demand.generate_solver_space_matrix.  Also,
       create negative demands (unload drive time) at break nodes, but
       only visit break nodes if need to do so.

    """
    # preprocess travel and service time to speed up solver
    number = len(travel_minutes_matrix)
    max_time = travel_minutes_matrix.max().max()
    penalty_time =  int(10000000 * max_time)

    node_list = [(n,demand,period,break_time) for n in travel_minutes_matrix.index]
    # print('len node list is ',len(node_list))
    ncpus = len(os.sched_getaffinity(0))
    p = Pool(ncpus)
    node_demand_service_list = p.map(make_drive_data,node_list)
    # print(node_demand_service_list)

    travel_times = p.map(f,iter.product(node_demand_service_list,repeat=2))
    df_stacked_service_time = pd.DataFrame(travel_times,columns=['from','to','service_time'])
    # print(df_stacked_service_time)
    df_service_time = df_stacked_service_time.pivot(index='from',columns='to',values='service_time')

    _total_time = (df_service_time + travel_minutes_matrix).fillna(penalty_time).values
    #print(df_service_time + travel_minutes_matrix)

    def time_callback(manager, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # print('drive time',from_node,to_node,_total_time[from_node][to_node])
        return _total_time[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return time_callback

def create_short_break_callback(travel_minutes_matrix,
                          demand,
                          period,
                          break_time):
    """create a callback function for short_breaktime.  presumes that
       travel_minutes_matrix is in solver space, not map space (has
       been passed through demand.generate_solver_space_matrix.  Also,
       create negative demands (unload short_break time) at break nodes, but
       only visit break nodes if need to do so.

    """
    # preprocess travel and service time to speed up solver
    number = len(travel_minutes_matrix)
    max_time = travel_minutes_matrix.max().max()
    penalty_time =  int(10000000 * max_time)

    node_list = [(n,demand,period,break_time) for n in travel_minutes_matrix.index]
    # print('len node list is ',len(node_list))
    ncpus = len(os.sched_getaffinity(0))
    p = Pool(ncpus)
    node_demand_service_list = p.map(make_drive_data,node_list)
    # print(node_demand_service_list)

    travel_times = p.map(e,iter.product(node_demand_service_list,repeat=2))
    df_stacked_service_time = pd.DataFrame(travel_times,columns=['from','to','service_time'])
    # print(df_stacked_service_time)
    df_service_time = df_stacked_service_time.pivot(index='from',columns='to',values='service_time')

    _total_time = (df_service_time + travel_minutes_matrix).fillna(penalty_time).values
    checkroute = [0, 4, 3, 6, 1, 11, 10, 13, 12, 15, 14, 17, 16, 2]
    print(travel_minutes_matrix.loc[checkroute,checkroute])
    print(df_service_time.loc[checkroute,checkroute])
    print((df_service_time + travel_minutes_matrix).loc[checkroute,checkroute])

    def time_callback(manager, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # print('drive time',from_node,to_node,_total_time[from_node][to_node])
        return _total_time[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return time_callback
