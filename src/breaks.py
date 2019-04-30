""" utilities for making break nodes between normal nodes """
import pandas as pd
import numpy as np
import math
import sys

def make_nodes(O,D,travel_time,starting_node):
    """starting with O, ending with D, make a dummy node every hour
    arguments: O: origin node, integer
               D: destination node, integer
               travel_time: time from O to D, in minutes
               starting_node: starting point for new nodes, integer
    returns: 2 dimensional array of travel times for new nodes.
             This array is one-directional, from O to D.  Nodes
             are numbered from zero, sequentially, and can be
             extracted from the keys of the array (ignore O and D)
    """

    # travel time is broken up into 60 minute chunks via
    # [i*60 + 60 for i in range (0,math.floor(travel_time/60))]

    num_new_nodes = math.floor(travel_time/60)
    if num_new_nodes > 300:
        print('trying to make more than 300 nodes (',
              num_new_nodes,
              ' to be exact).  300 nodes means a trip of more than 300 hours (12 days), which is unlikely.  check for bugs.  If you really want this behavior, then edit breaks.py')
        print(O,D,travel_time,starting_node)
    assert num_new_nodes < 300
    # if exactly some multiple of 60minutes, drop that last node
    if travel_time % 60 == 0:
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
        # compute travel minutes:  node = 0, 60 min; node = 1, 120, etc
        new_times[O][node] = 60*idx + 60
        new_times[node][node] = 0
        new_times[node][D] = travel_time - (60*idx + 60)
        if node > starting_node:
            for pidx in range(0,idx):
                prev_node=pidx+starting_node
                new_times[prev_node][node] = (idx - pidx) * 60

    # new nodes are stored in "new_times" as keys of second dimension
    # not symmetric, but rather, directional.  Opposite way is impossible
    # so those values are NaN and easily set to infinity
    return new_times

# function for applying to demand
# use closure for access to global
#
# FIXME this is ugly, and will not parallelize well, and therefore may
# not actually do what I want in some cases.  The problem is figuring
# out in advance where to start numbering the new nodes for each
# record, OR figuring out after the fact how to renumber the new nodes
# so that they make sense.  The approach below is setting the
# numbering deliberately.  A better approach would allow each
# invocation to be independent, maybe storing the results in a
# hashmap.
#

def break_generator(travel_times):
    min_start = len(travel_times[0]) + 1
    def gen_breaks(record):
        tt = travel_times.loc[record.origin,record.destination]
        new_times = make_nodes(record.origin,
                               record.destination,
                               tt,
                               min_start)
        return new_times

    return gen_breaks

def aggregate_time_matrix(travel_time,newtimes):
    """combine current time matrix with list of new times from gen_breaks, above"""

    max_new_node = len(travel_time[0])+1
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
