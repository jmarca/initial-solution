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

def split_links(O,D,travel_time,starting_node):
    """split the link from O to D in half
    arguments: O: origin node, integer
               D: destination node, integer
               travel_time: time from O to D, integer
               starting_node: starting point for new nodes, integer
    returns: 2 dimensional array of travel times for new nodes.
             This array is one-directional, from O to D.  Nodes
             are numbered from starting_node + zero, sequentially
    """

    new_times = {}
    new_times[O] = {}
    new_times[D] = {}
    new_times[O][O] = 0
    new_times[O][D] = travel_time
    new_times[D][D] = 0

    node = starting_node
    new_times[node] = {}
    # compute travel minutes
    new_times[O][node] = math.floor(travel_time/2)
    new_times[node][node] = 0
    new_times[node][D] = travel_time - new_times[O][node]

    # new nodes are stored in "new_times" as keys of second dimension
    # not symmetric, but rather, directional.  Opposite way is impossible
    # so those values are NaN and easily set to infinity
    return new_times




def make_dummy_node(travel_times,pickups,dropoffs,start=-1):
    """create dummy node.  Expand travel time matrix"""
    # create a dummy node, only reachable from depot,
    new_times = {}
    # new node id
    nn_id = start
    if start < 0:
        nn_id = int(travel_times.index.max()) + 1
    new_times[0] = {0:0}
    new_times[nn_id] = {0:0}
    # now all set travel time from nn to all pickups equal to depot to pickups
    # for p in pickups:
    #     new_times[nn_id][p]=travel_times.loc[0,p]
    for p in dropoffs:
        new_times[p]={}
        new_times[p][nn_id]=travel_times.loc[p,0]
    new_times[0][nn_id]=0
    new_times[nn_id][nn_id]= 0

    return new_times

def make_dummy_vehicle_nodes(vehicles,travel_times,pickups,dropoffs):
    moretimes = []
    start = travel_times.index.max()+1
    new_times = make_dummy_vehicle_node(travel_times,pickups,dropoffs,start)
    moretimes.append(new_times)
    for v in range(1,len(vehicles.vehicles)):
        # for now, just do it every time
        # but eventually should figure out logic to copy in from new_times
        start += 1
        new_times = make_dummy_vehicle_node(travel_times,pickups,dropoffs,start)
        moretimes.append(new_times)
    return moretimes


# functions for applying to demand
# use closure for access to global
#
def break_generator(travel_times,timelength=600):
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

def split_generator(travel_times,timelength=600):
    def gen_breaks(record):
        min_start = len(travel_times.index)
        new_times = []
        idx = 0
        tt = travel_times.loc[0,record.origin]
        if tt > timelength:
            new_times.append( split_links(0,record.origin,
                                           tt,
                                           min_start))
            min_start += 1
            idx += 1
        tt = travel_times.loc[record.origin,record.destination]
        if tt > timelength:
            new_times.append( split_links(record.origin,
                                          record.destination,
                                          tt,
                                          min_start))
            min_start += 1
            idx += 1
        tt = travel_times.loc[record.destination,0]
        if tt > timelength:
            new_times.append( split_links(record.destination,0,
                                    tt,
                                    min_start))
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
        #print(max_new_node,'<-\n',new_df)
        #assert 0
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

def aggregate_dummy_nodes(travel_time,newtimes):
    """combine current time matrix with list of new times for each new node"""

    max_new_node = len(travel_time.index)
    for nt in newtimes:
        # print(nt)
        new_df = pd.DataFrame.from_dict(data=nt,orient='index')
        # print (new_df)
        old_cols = [i for i in new_df.columns.view(int)]
        old_cols.sort() # shift new node to last
        new_cols = [old_cols.pop()]
        # print(new_cols,old_cols)
        #print(new_df.loc[new_cols,old_cols])
        #print(new_df.loc[old_cols,new_cols])
        # assert 0
        # first append the new destinations for existing columns
        travel_time = travel_time.append(new_df.loc[new_cols,old_cols])

        # if debug:
        # print(travel_time)
        # then join in the new rows and columns
        reduced_df = new_df.loc[:,new_cols]
        reduced_df = reduced_df.reindex()
        travel_time = travel_time.join(reduced_df
                                       ,how='outer'
        )
    # now replace NaN with infinity
    # travel_time = travel_time.fillna(sys.maxsize)
    # print(travel_time)
    return travel_time

def aggregate_split_nodes(travel_time,newtimes):
    """combine current time matrix with list of new times for each new node"""
    def agg_fn(nt,tt_matrix):
        max_old_node = tt_matrix.index.max()
        new_df = pd.DataFrame.from_dict(data=nt,orient='index')
        old_cols = [i for i in new_df.columns.view(int)]
        old_cols.sort() # shift new node to last
        new_cols = [old_cols.pop()]
        # need to adjust the dataframe so no overlapping new columns
        offset = (max_old_node+1) - min(new_df.loc[:,new_cols].columns)
        # first the columns
        adjustment = [0  for i in range(0,len(new_df.columns))]
        adjustment[-1] = offset
        if offset > 0:
            new_df.columns = [i + adj for (i,adj) in zip(new_df.columns,adjustment)]
            new_df.index = [i + adj for (i,adj) in zip(new_df.index,adjustment)]
            new_df = new_df.reindex()
            new_cols = new_df.index.max()
        # first append the new destinations for existing columns

        tt_matrix = tt_matrix.append(new_df.loc[new_cols,old_cols])
        # if debug:
        # print(tt_matrix)
        # then join in the new rows and columns
        reduced_df = new_df.loc[:,new_cols]
        reduced_df = reduced_df.reindex()
        return tt_matrix.join(reduced_df
                                ,how='outer'
        )

    for nt in newtimes:
        if len(nt) == 0:
            continue
        # nt is now an array, of 1 or 3 values, depending
        for nt_entry in nt:
            travel_time = agg_fn(nt_entry,travel_time)

        # loop
    # now replace NaN with infinity
    # travel_time = travel_time.fillna(sys.maxsize)
    # print(travel_time)
    return travel_time


def breaks_logic():
    node_visit_transit = {}
    for n in expanded_mm.index:
        node_visit_transit[n] = int(d.get_service_time(n))

    breaks = {}
    constraints = {}
    starts = []
    slacks = []
    ends   = []
    # grab ref to solver
    solver = routing.solver()

    # min_intervals = d.get_min_intervals(len(vehicles.vehicles))
    first_breaks = d.get_first_break(len(vehicles.vehicles),mm)
    print(first_breaks)

    for i in range(0,len(vehicles.vehicles)):
        print ( 'breaks for vehicle',i)
        breaks[i] = []
        constraints[i] = []
        active_start =  routing.ActiveVar(routing.Start(i))
        active_end = routing.VehicleVar(routing.End(i)) == i
        counting_end = active_end * count_dimension.CumulVar(routing.End(i))
        end_count_okay = counting_end > 1
        active_vehicle = end_count_okay
        time_start = time_dimension.CumulVar(routing.Start(i))
        slack_start = time_dimension.SlackVar(routing.Start(i))
        time_end = time_dimension.CumulVar(routing.End(i))
        must_start = active_vehicle*(time_start + slack_start + 11*60) # 11 hours later

        for pickup_node in first_breaks.keys():
            fb = first_breaks[pickup_node]
            # set up the origin details for constraints
            pickup_idx = manager.NodeToIndex(pickup_node)
            active_node = routing.ActiveVar(pickup_idx)
            same_vehicle_condition = active_node * routing.VehicleVar(pickup_idx) == i

            for j in range(0,len(fb)):
                pair = fb[j]
                jth_10hr_break = solver.FixedDurationIntervalVar(
                    pair[0],  # minimum start time
                    pair[1],  # maximum start time
                    10 * 60,      # duration of break is 10 hours
                    True,         # optional, condition on vehicle serving origin
                    '10hr break {} for vehicle {} serving {}'.format(j,i,pickup_node))
                breaks[i].append(jth_10hr_break)
                # first pickup constraint---breaks only relevant if first pickup
                # due to split long nodes, count dimension might be 1 or 2
                count_val = active_node * count_dimension.CumulVar(pickup_idx)
                counted_visit = count_val >= 1
                early_visit = count_val <= 2
                break_active_condition = counted_visit*early_visit
                # only use if this vehicle actually serves the intended node
                cond_expr = solver.ConditionalExpression(
                    same_vehicle_condition,
                    jth_10hr_break.PerformedExpr() == break_active_condition,
                    1)
                solver.Add(cond_expr>=1)
                print('break',len(breaks[i])-1,'for serving node',pair[2])

        # now add additional breaks for whole of likely range
        # break up full time (horizon) into 10+11 hour ranges (drive 11, break 10)
        # not quite right, as the 14hr rule also comes into play

        need_breaks = math.floor(args.horizon / 60 / (10 + 11))
        #need_breaks -= min_intervals[i]
        # need_breaks = 0
        # follow_constraints = []
        # don't need first break, as that is already specified above
        # if i > 0:
        #     need_breaks = 2

        # # start counting from?
        # for intvl in range(len(fb),need_breaks):
        #     print(intvl)
        #     # break minimum start time is 0
        #     # break maximum start time is horizon - 10 hours

        #     min_start_time = (intvl)*(10 + 11)*60
        #     max_start_time = (intvl)*(10 + 11)*60 + 660

        #     if min_start_time > args.horizon - 660:
        #         break

        #     require_first_few = False
        #     #if intvl > 0:
        #     #    require_first_few = True
        #     # key on first break, but only required if time hasn't run out
        #     # next_10hr_break = solver.FixedDurationStartSyncedOnEndIntervalVar(
        #     #     breaks[i][-1],      # keyed to prior
        #     #     600,               # duration
        #     #     660     # offset
        #     # )
        #     next_10hr_break = solver.FixedDurationStartSyncedOnStartIntervalVar(
        #         breaks[i][0],      # keyed to first
        #         600,               # duration
        #         min_start_time     # offset
        #     )
        #     # next_10hr_break = solver.FixedDurationIntervalVar(
        #     #     min_start_intvar,  # maximum start time (11 hours after start)
        #     #     10 * 60,     # duration of break is 10 hours
        #     #     '10hr break {} for vehicle {}'.format(intvl,i))
        #     # next_10hr_break = solver.FixedDurationIntervalVar(
        #     #     min_start_time, # minimum start time
        #     #     max_start_time,  # maximum start time (11 hours after start)
        #     #     10 * 60,     # duration of break is 10 hours
        #     #     optional,       # optional?
        #     #     '{}th 10hr break for vehicle {}'.format(intvl,i))

        #     breaks[i].append(next_10hr_break)
        #     # constraints:
        #     # bip = next_10hr_break.MustBePerformed()
        #     # solver.Add(next_10hr_break.PerformedExpr()==True)
        #     # print('break must be performed = ',bip)
        #     # sync with preceding break
        #     #  this break starts 11h after end of prior
        #     # follow_after_constraint = next_10hr_break.StartsAfterEndWithDelay(
        #     #     breaks[i][intvl-1],
        #     #     660) # 11 hours times 60 minutes = 660
        #     # solver.Add(follow_after_constraint)


        #     if require_first_few:
        #         # conditional constraint.  If vehicle is done before start
        #         # time, then don't bother with this break

        #         # first, requirement that break is performed
        #         break_condition = next_10hr_break.PerformedExpr()==True

        #         # second, the timing.  If route is over, don't need break
        #         break_start = time_start + intvl*(11+10)*60
        #         time_condition =  break_start < time_end # break_start

        #         # use conditional expression
        #         expression = solver.ConditionalExpression(time_condition,
        #                                                   break_condition,
        #                                                   1)
        #         solver.AddConstraint(
        #             expression >= 1
        #         )

        #     # print(follow_after_constraint)
        #     # follow_constraints.append(follow_after_constraint)
        print(breaks[i])
        time_dimension.SetBreakIntervalsOfVehicle(
            breaks[i], i, node_visit_transit)

        # for follow_after_constraint  in follow_constraints:
        #     solver.Add(follow_after_constraint)
