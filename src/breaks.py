""" utilities for making break nodes between normal nodes """
# import pandas as pd
import math

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
