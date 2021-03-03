# create simple 2D array for distance lookup?
# Define cost of each arc.
import numpy as np
import sys
import os
import pandas as pd
from multiprocessing import Pool
import itertools as iter

def create_demand_callback(nodes,demand):
    """ create a callback function for demand """
    _demand = {}
    for idx in range(0,len(nodes)):
        node = nodes[idx]
        _demand[idx] = demand.get_demand(node)
    print('size of demand matrix is ',len(_demand))
    def demand_callback(manager, index):
        """Returns the demand at the index, if defined, or zero."""
        # Convert from routing variable Index to demand array Node.
        node = manager.IndexToNode(index)
        # print('demand callback with',node)
        # print('demand callback with',node,_demand[node])
        return _demand[node]


    # return the callback, which will need to be set up with partial
    return demand_callback

def lookup_function_generator(_total_time):
    def lookup_function(manager,from_index,to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # print('drive time',from_node,to_node,_total_time[from_node][to_node])
        return int(_total_time[from_node][to_node])

    # return the callback, which will need to be set up with partial
    return lookup_function

# def weighted_lookup_function_generator(_total_time, dim):
#     def lookup_function(manager,from_index,to_index):
#         """Returns the travel time between the two nodes."""
#         # Convert from routing variable Index to distance matrix NodeIndex.
#         from_node = manager.IndexToNode(from_index)
#         to_node = manager.IndexToNode(to_index)
#         # query dim.  if greater than 5, double this dimension
#         if dim.cumulVar(from_index) > 5:
#             print('drive time',from_node,to_node,_total_time[from_node][to_node])
#             return int(2* (_total_time[from_node][to_node]))
#         else:
#             print('drive time',from_node,to_node,_total_time[from_node][to_node])
#         return int(_total_time[from_node][to_node])

#     # return the callback, which will need to be set up with partial
#     return lookup_function



def create_dist_callback(dist_matrix,
                         demand):
    """ create a callback function for dist """
    # dist matrix is now in model space, not map space
    # preprocess travel and service dist to speed up solver

    max_dist = dist_matrix.max().max()
    penalty_dist =  int(10000000 * max_dist)
    _total_dist = dist_matrix.fillna(penalty_dist).values

    return lookup_function_generator(_total_dist)


def create_time_callback2(travel_minutes_matrix,
                          demand):
    """Time callback version 2

       Use this one if breaks happen at nodes.  The difference with
       create_time_callback is that break nodes here (those with zero
       demand, etc) have a service time of 11 hours, to simulate
       taking the break.

    """
    # preprocess travel and service time to speed up solver
    size = len(travel_minutes_matrix)

    service_time = np.zeros((size,size))
    notna = travel_minutes_matrix.notna()
    tmm_index = travel_minutes_matrix.index
    # service time is determined by from node
    for o_idx in tmm_index:
        o_sv = demand.get_service_time(o_idx)
        o_bk = demand.get_break_node(o_idx)
        if o_bk:
            o_sv = o_bk.break_time
        for d_idx in tmm_index[notna.loc[o_idx,:]]:
            if o_idx != d_idx:
                service_time[o_idx,d_idx] = o_sv

    _total_time = gen_total_time(service_time,travel_minutes_matrix)
    return lookup_function_generator(_total_time)


def gen_total_time(service,times):
    max_time = times.max().max()
    penalty_time =  int(10000000 * max_time)
    df_service_time = pd.DataFrame(service)
    _total_time = (df_service_time + times).fillna(penalty_time).values
    return _total_time

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

    #node_list = [(n,demand,period,break_time) for n in travel_minutes_matrix.index]
    # print('len node list is ',len(node_list))
    #ncpus = 3#len(os.sched_getaffinity(0))
    #p = Pool(ncpus)
    #node_demand_service_list = p.map(make_drive_data,node_list)
    # print(node_demand_service_list)

    size = len(travel_minutes_matrix)
    service_time = np.zeros((size,size))
    notna = travel_minutes_matrix.notna()
    tmm_index = travel_minutes_matrix.index
    # service time is determined by from node
    for o_idx in tmm_index:
        o_sv = 0
        o_bk = demand.get_break_node(o_idx)
        if o_bk:
            # drive callback only wants to know breaks of 600
            if o_bk.break_time >= break_time:
                o_sv = o_bk.drive_time_restore()
        # again, from node is important
        for d_idx in tmm_index[notna.loc[o_idx,:]]:
            if o_idx != d_idx:
                service_time[o_idx,d_idx] = o_sv

    _total_time = gen_total_time(service_time,travel_minutes_matrix)
    return lookup_function_generator(_total_time)


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
    if period < 0:
        period = period * -1
    # preprocess travel and service time to speed up solver
    size = len(travel_minutes_matrix)
    service_time = np.zeros((size,size))
    notna = travel_minutes_matrix.notna()
    tmm_index = travel_minutes_matrix.index

    # service time is determined by from node
    for o_idx in tmm_index:
        o_sv = 0
        value = 0
        o_bk = demand.get_break_node(o_idx)
        if o_bk:
            # short break callback gets benefits from both short and long breaks
            if o_bk.break_time >= break_time:
                o_sv = o_bk.drive_time_restore()
                value = o_sv
                if o_sv < -period:
                    # after trying a few things, it is never true that
                    # a long break happens without a preceding short
                    # break.  Therefore, if this is a long break, an
                    # earlier short break already pushed the clock
                    # back on the counter by 480, so here I only want
                    # to push it back another 3 hours (to get it
                    # aligned with the 11 hr long break timing
                    value = -3*60 # same as o_sv - (-period)

        # bail out if just going to assign 0
        if o_sv != 0:
            # again, from node is important, but here have to consider if
            # moving from break to break
            for d_idx in tmm_index[notna.loc[o_idx,:]]:
                if o_idx != d_idx:
                    service_time[o_idx,d_idx] = value

    _total_time = gen_total_time(service_time,travel_minutes_matrix)
    return lookup_function_generator(_total_time)
