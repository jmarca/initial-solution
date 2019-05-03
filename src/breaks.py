""" utilities for making break nodes between normal nodes """
import pandas as pd
import numpy as np
import math
import sys

def make_nodes(O,D,travel_time,starting_node,timelength=60):
    """starting with O, ending with D, make a dummy node every timelength minutes
    arguments: O: origin node, integer
               D: destination node, integer
               travel_time: time from O to D, in minutes
               starting_node: starting point for new nodes, integer
               timelength: size of each segment, minutes, default 60
    returns: 2 dimensional array of travel times for new nodes.
             This array is one-directional, from O to D.  Nodes
             are numbered from zero, sequentially, and can be
             extracted from the keys of the array (ignore O and D)
    """

    # travel time is broken up into timelength minute chunks via
    # [i*timelength + timelength for i in range (0,math.floor(travel_time/timelength))]

    num_new_nodes = math.floor(travel_time/timelength)
    if num_new_nodes > 100:
        print('trying to make more than 100 nodes (',
              num_new_nodes,
              ' to be exact).  100 nodes means for any reasonable sized network, this will never run.  check for bugs.  If you really want this behavior, then edit breaks.py')
        print(O,D,travel_time,starting_node)
    assert num_new_nodes < 100
    # if exactly some multiple of timelength minutes, drop that last node
    if travel_time % timelength == 0:
        num_new_nodes -= 1

    new_times = {}
    new_times[O] = {}
    new_times[D] = {}
    new_times[O][O] = 0
    new_times[O][D] = travel_time
    new_times[D][D] = 0

    for idx in range(0,num_new_nodes):
        node = idx+starting_node
        new_times[node] = {}
        # compute travel minutes:  node = 0, timelength min; node = 1, 120, etc
        new_times[O][node] = timelength*idx + timelength
        new_times[node][node] = 0
        new_times[node][D] = travel_time - (timelength*idx + timelength)
        if node > starting_node:
            for pidx in range(0,idx):
                prev_node=pidx+starting_node
                new_times[prev_node][node] = (idx - pidx) * timelength

    # new nodes are stored in "new_times" as keys of second dimension
    # not symmetric, but rather, directional.  Opposite way is impossible
    # so those values are NaN and easily set to infinity
    return new_times

# function for applying to demand
# use closure for access to global
#

def break_generator(travel_times,timelength=60):
    min_start = len(travel_times.index)
    def gen_breaks(record):
        tt = travel_times.loc[record.origin,record.destination]
        new_times = make_nodes(record.origin,
                               record.destination,
                               tt,
                               min_start,
                               timelength)
        return new_times

    return gen_breaks

def aggregate_time_matrix(travel_time,newtimes):
    """combine current time matrix with list of new times from gen_breaks, above"""

    max_new_node = len(travel_time.index)
    for nt in newtimes:
        if len(nt) < 3:
            # don't bother with no new nodes case
            continue
        new_df = pd.DataFrame.from_dict(data=nt,orient='index')
        #new_df = new_df.fillna(sys.maxsize)
        new_cols = [i for i in range(2,len(new_df))]
        old_cols = [0,1]

        # need to adjust the dataframe
        offset = max_new_node - min(new_df.iloc[:,new_cols].columns)
        # print(max_new_node,offset)

        # first the columns
        adjustment = [offset  for i in range(0,len(new_df.columns))]
        # if debug:
        #     print(adjustment)
        adjustment[0] = 0
        adjustment[1] = 0
        # if debug:
        #     print(new_df.columns)
        new_df.columns = [i + adj for (i,adj) in zip(new_df.columns,adjustment)]
        # if debug:
        #     print(new_df.columns)
        # then the rows (index)
        new_df.index = [i + adj for (i,adj) in zip(new_df.index,adjustment)]
        new_df = new_df.reindex()

        max_new_node = new_df.columns.max()+1

        # if debug:
        #print(new_df)
        # first append the new destinations for existing columns
        travel_time = travel_time.append(new_df.iloc[new_cols,old_cols])
        #print(travel_time)

        # if debug:
        #     print(travel_time)
        # then join in the new rows and columns
        reduced_df = new_df.iloc[:,new_cols]
        reduced_df = reduced_df.reindex()
        # if debug:
        #print(reduced_df)
        travel_time = travel_time.join(reduced_df
                                       ,how='outer'
        )
        # if debug:
        # print(travel_time)

        # if debug:
        # assert 0

    # now replace NaN with infinity
    # travel_time = travel_time.fillna(sys.maxsize)
    # print(travel_time)
    return travel_time
