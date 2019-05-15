import pandas as pd
import numpy as np
import itertools
import read_csv as reader
import breaks
import sys
import math

"""Functions for setting up intial routes"""


def cycle_goal(origin,destination):
    def cycler(goal):
        if goal == 0:
            return -1
        if goal==origin:
            return destination
        return 0
    return cycler


def initial_routes(demand,vehicles,time_matrix,
                   manager,time_callback,drive_callback,short_callback,
                   debug=False):#,time_callback,drive_callback):
    # initial routes should be a list of nodes to visit, in node space
    # (not solver index space, not map space)

    # assign one route per vehicle
    veh = 0
    prior = 0
    feasible_idx = demand.demand.feasible
    trip_chains = {}
    travel_times = {}
    drive_times = {}
    short_times = {}

    for idx in demand.demand.index[feasible_idx]:
        if veh >= len(vehicles):
            break
        reached_depot = False
        trip_chain = []
        record = demand.demand.loc[idx,:]
        if debug:
            print (record)
        prior = 0 # depot node

        cycler = cycle_goal(record.origin,record.destination)
        goal = record.origin

        tt = 0
        dt = 0
        travel_time = 0
        drive_time  = 0
        short_time  = 0
        # print('before',travel_time,drive_time)
        while not reached_depot:

            # considering trip from prior to goal
            # either insert a break node, or insert goal
            # what is travel time from prior to goal?
            tt_prior_goal = time_matrix.loc[prior,goal]

            if ((drive_time + tt_prior_goal < 660 ) and
                (short_time + tt_prior_goal < 480 )):

                if debug:
                    print('go straight to goal',
                          'tt_prior_goal',tt_prior_goal,
                          'prior',prior,
                          'goal',goal,
                          'dt',dt,
                          'drive_time',drive_time,
                          'tt',tt,
                          'travel_time',travel_time,'\n',record)

                # just go straight to goal
                tt += time_callback(manager.NodeToIndex(prior),
                                    manager.NodeToIndex(goal))
                dt += drive_callback(manager.NodeToIndex(prior),
                                     manager.NodeToIndex(goal))
                travel_time += tt_prior_goal + demand.get_service_time(prior)
                drive_time += tt_prior_goal
                short_time += tt_prior_goal


                next_goal = cycler(goal)
                reached_depot = next_goal == -1
                if not reached_depot:
                    trip_chain.append(goal)
                    prior = goal
                # assertion checks about conditions
                if goal == record.origin:
                    # check that time window requirements are satisfied
                    # print(record.from_node,record.origin,record.early,tt,record.late)
                    if debug:
                        print(record,'\n',
                              'tt',tt,
                              'travel_time',travel_time,
                              'dt',dt,
                              'drive_time',drive_time,
                              'short time',short_time)
                    assert tt+record.pickup_time  -1 <= record.depot_origin
                    assert record.depot_origin <= tt+1 + record.pickup_time
                goal = next_goal
                continue
            else:
                # cannot go straight from prior to goal.  Must go to at least one break

                # pick either a short break or a long break.
                # decision rule: if short time plus drive to next long break is
                # over 8 * 60, need to short break
                break_list = demand.get_break_node_chain(prior,goal)
                breaks = [demand.get_break_node(bk) for bk in break_list]
                if debug:
                    print(break_list)
                if break_list == None:
                    print('missing break list for',prior,goal)
                    assert 0
                # fr keeps track of "from" break node
                fr = prior
                sbrk_idx = 0
                lbrk_idx = 0
                brk_idx = 0
                tt_fr_goal = time_matrix.loc[fr,goal]
                while (brk_idx < len(break_list) and
                       (drive_time + tt_fr_goal >= 660 ) or
                       (short_time + tt_fr_goal >= 480 )):
                    sbk = breaks[brk_idx]
                    lbk = breaks[brk_idx+1]
                    if sbk.break_time != 30:
                        if lbk.break_time == 30:
                            sbk = lbk
                            brk_idx += 1
                            lbk = breaks[brk_idx+1]
                    print(brk_idx,sbk.break_time,30,lbk.break_time,600)
                    assert lbk.break_time == 600
                    assert sbk.break_time == 30

                    tt_fr_lbk = time_matrix.loc[fr,lbk.node]
                    tt_fr_sbk = time_matrix.loc[fr,sbk.node]
                    tt_sbk_lbk = time_matrix.loc[sbk.node,goal]
                    tt_lbk_goal = time_matrix.loc[lbk.node,goal]
                    # in the zeroth case, must visit one of the break nodes
                    # test short break first
                    take_sbk = False
                    take_lbk = False
                    if (drive_time + tt_fr_goal) >= 660:
                        # will need to take long break
                        take_lbk = True
                        # lbk can satisfy for short break, unless it will
                        # take > 8hr to get to lbk
                        if short_time + tt_fr_lbk >= 480:
                            # will need to take short break
                            take_sbk = True
                    else:
                        if debug:
                            print('do not need long break, drive time + remaining is', drive_time + tt_fr_goal, 660)
                    if short_time + tt_fr_goal >= 480:
                        # will need to take long break
                        take_sbk = True

                    if take_sbk:
                        trip_chain.append(sbk.node)
                        short_time += tt_fr_sbk + sbk.drive_time_restore()
                        drive_time += tt_fr_sbk
                        fr = sbk.node
                        tt_fr_lbk = time_matrix.loc[fr,lbk.node]
                        if debug:
                            print('take short brk',sbk.node,short_time,drive_time)

                    else:
                        if debug:
                            print('did not take short break',
                                  'drive_time',drive_time,
                                  'fr_goal',tt_fr_goal,
                                  drive_time+tt_fr_goal)
                    if take_lbk:
                        trip_chain.append(lbk.node)
                        drive_time += tt_fr_lbk + lbk.drive_time_restore()
                        short_time += tt_fr_lbk - (660 - 480) # hack
                        fr = lbk.node
                        if debug:
                            print('take long brk',lbk.node,short_time,drive_time)
                    tt_fr_goal = time_matrix.loc[fr,goal]

                    brk_idx += 1

                # okay, done adding breaks, now what?
                # at the goal, so add that and account for it
                short_time += tt_fr_goal
                drive_time += tt_fr_goal

                next_goal = cycler(goal)
                reached_depot = next_goal == -1
                if not reached_depot:
                    trip_chain.append(goal)
                    prior = goal
                    goal = next_goal
                    tt_prior_goal = time_matrix.loc[prior,goal]
                if debug:
                    print('chain is',trip_chain,
                          'short time',short_time,
                          'drive time',drive_time
                    )


        # examine chain and insert 30 min breaks before every 11 hr
        # break---because I'm too lazy to do that above right now, so
        # let's see if this gives the solver a good enough start
        # expanded_chain = []
        print(trip_chain) # before

        # loop to next demand, next trip chain, next vehicle
        trip_chains[veh] = trip_chain
        travel_times[veh] = travel_time
        drive_times[veh] = drive_time
        short_times[veh] = short_time
        veh += 1
        prior = 0
        travel_time = 0
        drive_time = 0
    # print(time_matrix)
    # print(trip_chains)
    # print(travel_times)
    # print(drive_times)
    # print(short_times)

    return trip_chains
