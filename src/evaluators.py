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
    # preprocess travel and service time to speed up solver
    number = len(travel_minutes_matrix)
    max_time = travel_minutes_matrix.max().max()
    penalty_time =  int(10000000 * max_time)

    _total_time = penalty_time * np.ones((number,number))

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

    # travel_times = p.map(f,iter.product(node_demand_service_list,repeat=2))
    # df_stacked_service_time = pd.DataFrame(travel_times,columns=['from','to','service_time'])
    # print(df_stacked_service_time)
    #df_service_time = df_stacked_service_time.pivot(index='from',columns='to',values='service_time')
    df_service_time = pd.DataFrame(service_time)
    # check_chain = [0, 4, 3, 6, 5, 1, 13, 12, 15, 14, 17, 16, 2, 22, 21, 24, 23]
    # print(df_service_time.loc[check_chain,check_chain])
    # print(travel_minutes_matrix.loc[check_chain,check_chain])
    # print((df_service_time + travel_minutes_matrix).loc[check_chain,check_chain])
    _total_time = (df_service_time + travel_minutes_matrix).fillna(penalty_time).values
    # print (pd.DataFrame.from_dict(_total_time,orient='index'))
    # assert 0

    def time_callback(manager, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # print('time',from_node,to_node,_total_time[from_node,to_node])
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

    # travel_times = p.map(f,iter.product(node_demand_service_list,repeat=2))
    # df_stacked_service_time = pd.DataFrame(travel_times,columns=['from','to','service_time'])
    # # print(df_stacked_service_time)
    # df_service_time = df_stacked_service_time.pivot(index='from',columns='to',values='service_time')
    df_service_time = pd.DataFrame(service_time)

    _total_time = (df_service_time + travel_minutes_matrix).fillna(penalty_time).values
    #print(df_service_time + travel_minutes_matrix)
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
    number = len(travel_minutes_matrix)
    max_time = travel_minutes_matrix.max().max()
    penalty_time =  int(10000000 * max_time)

    # node_list = [(n,demand,period,break_time) for n in travel_minutes_matrix.index]
    # # print('len node list is ',len(node_list))
    # ncpus = 3 #len(os.sched_getaffinity(0))
    # p = Pool(ncpus)
    # node_demand_service_list = p.map(make_drive_data,node_list)
    # # print(node_demand_service_list)

    size = len(travel_minutes_matrix)
    service_time = np.zeros((size,size))
    notna = travel_minutes_matrix.notna()
    tmm_index = travel_minutes_matrix.index
    # check_chain = [0, 4, 3, 6, 5, 1, 13, 12, 15, 14, 17, 16, 2, 22, 21, 24, 23]
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
                    # d_sv = 0
                    # d_bk = demand.get_break_node(d_idx)
                    # if d_bk:# and d_bk.break_time >= break_time:
                    #     d_sv = d_bk.drive_time_restore()
                    # # compare two service times
                    # # if o_idx in check_chain and d_idx in check_chain:
                    # #     print(o_idx,o_sv,d_idx,d_sv)
                    # if d_sv >= 0:
                    #     # moving from break to not break
                    #     service_time[o_idx,d_idx] = value
                    # else:
                    #     # moving between breaks.
                    #     if o_sv == -period and d_sv < -period:
                    #         # moving from short to long
                    #         # hardcoded hack
                    #         service_time[o_idx,d_idx] = d_sv - value
                    #     if o_sv < -period and d_sv == -period:
                    #         # moving from long to short
                    #         service_time[o_idx,d_idx] = value
                    #     if d_sv < -period and o_sv < -period:
                    #         # moving from long to long
                    #         # shouldn't ever happen in practice, but whatever
                    #         service_time[o_idx,d_idx] = value


    # travel_times = p.map(e,iter.product(node_demand_service_list,repeat=2))
    # df_stacked_service_time = pd.DataFrame(travel_times,columns=['from','to','service_time'])
    # # print(df_stacked_service_time)
    # df_service_time = df_stacked_service_time.pivot(index='from',columns='to',values='service_time')
    df_service_time = pd.DataFrame(service_time)

    _total_time = (df_service_time + travel_minutes_matrix).fillna(penalty_time).values
    # check_chain = [0, 4, 3, 6, 5, 1, 13, 12, 15, 14, 17, 16, 2, 22, 21, 24, 23]
    # print(df_service_time.loc[check_chain,check_chain])
    # print(travel_minutes_matrix.loc[check_chain,check_chain])
    # print((df_service_time + travel_minutes_matrix).loc[check_chain,check_chain])


    def time_callback(manager, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # print('short time',from_node,to_node,_total_time[from_node][to_node])
        return _total_time[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return time_callback



### deprecated
###
### the following functions were used for older version that used
### parallel processing (and that created a massive memory leak)

# def g(pair):
#     (a,b) = pair
#     (from_node,from_demand,from_service) = a
#     (to_node,to_demand,to_service) = b
#     value = to_service
#     if from_node == to_node:
#         value = 0
#     return [from_node,to_node,value]

# def f(pair):
#     (a,b) = pair
#     (from_node,from_demand,from_service) = a
#     (to_node,to_demand,to_service) = b
#     value = from_service
#     if from_node == to_node:
#         value = 0
#     return [from_node,to_node,value]

# # this one is for short breaks.
# # short breaks cannot get two 8hr restores in a row
# def e(pair):
#     (a,b) = pair
#     (from_node,from_demand,from_service) = a
#     (to_node,to_demand,to_service) = b
#     value = from_service
#     if value < -480:
#         value = -480
#     if from_node == to_node:
#         value = 0
#     # FIXME this is a quick and dirty hack
#     if value < 0 and from_service == -480 and  to_service == -660:
#         value = -3*60 # 11 hrs minus 8 hrs.  Don't want to get greedy
#     return [from_node,to_node,value]


# # this function works to set up impact of any node on total time
# # breaks add break_time to cumulative time
# # pickup and delivery nodes add service time to cumulative time
# # depot nodes add nothing
# def make_location_data(pair):
#     (node,demand) = pair
#     service_time = demand.get_service_time(node)
#     d = demand.get_demand(node)
#     break_node = demand.get_break_node(node)
#     if break_node != None:
#         service_time = break_node.break_time
#     return (node,d,service_time)

# # this function works to set up impact of a break node on the drive time dimensions
# # The 11 hr rule resets both the 30 minute break and the 10 hr break
# # The 8hr rule resets just the 30 minute break
# # so the if statement filters out any impact the 30 min break might have on the
# # 11 hr rule counter
# def make_drive_data(pair):
#     (node,demand,period,break_time) = pair
#     service_time = 0
#     d = demand.get_demand(node)
#     break_node = demand.get_break_node(node)
#     if break_node != None:
#         # duck typing of a sorts
#         if break_node.break_time >= break_time and abs(break_node.drive_time_restore())>=period:
#             # quacks like the duck we're looking for
#             service_time = break_node.drive_time_restore()
#     return (node,d,service_time)
