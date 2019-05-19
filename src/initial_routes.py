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

            if debug:
                print('loop',
                      'prior',prior,
                      'goal',goal)

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
                while (brk_idx + 1 < len(breaks)) and (
                        (drive_time + tt_fr_goal >= 660 ) or
                        (short_time + tt_fr_goal >= 480 )):
                    sbk = breaks[brk_idx]
                    lbk = breaks[brk_idx+1]
                    # if sbk.break_time != 30:
                    #     if lbk.break_time == 30:
                    #         sbk = lbk
                    #         brk_idx += 1
                    #         lbk = breaks[brk_idx+1]
                    if debug:
                        print('break index',brk_idx,
                              'short break',sbk.break_time,
                              'long break',lbk.break_time)
                    assert lbk.break_time == 600
                    assert sbk.break_time == 30

                    tt_fr_goal = time_matrix.loc[fr,goal]
                    tt_fr_lbk = time_matrix.loc[fr,lbk.node]
                    tt_fr_sbk = time_matrix.loc[fr,sbk.node]
                    tt_sbk_lbk = time_matrix.loc[sbk.node,goal]
                    tt_lbk_goal = time_matrix.loc[lbk.node,goal]
                    if debug:
                        print('tt remaining to goal',tt_fr_goal,
                              'tt to short break',tt_fr_sbk,
                              'tt to long break',tt_fr_lbk)

                    # test long break first
                    take_sbk = False
                    take_lbk = False
                    if (drive_time + tt_fr_goal) >= 660:
                        if debug:
                            print('lbk true',lbk.node,
                                  'drive time',drive_time,
                                  'tt to goal',tt_fr_goal,
                                  'sum',drive_time+tt_fr_goal,
                                  'tt to long break',tt_fr_lbk,
                                  'sum',drive_time+tt_fr_lbk)
                        # will need to take long break
                        take_lbk = True
                        # lbk can satisfy for short break, unless it will
                        # take > 8hr to get to lbk
                        # but break opportunities are NOT lined up
                        # with 660, 480, so account for that wrinkle

                        actual_break = tt_fr_lbk
                        if tt_fr_lbk < 660:
                            actual_break = 660 - drive_time
                        if (short_time + actual_break )>= 480:
                            if debug:
                                print('must take short break on way to long break',
                                      'short time',short_time,
                                      'tt to long break',tt_fr_lbk,
                                      'sum',short_time + tt_fr_lbk,
                                      'tt to short break',tt_fr_sbk,
                                      'sum',short_time + tt_fr_sbk,
                                )
                            # will need to take short break
                            take_sbk = True
                        else:
                            if debug:
                                print('will not take short break on way to long break',
                                      '\nfrom node',fr,
                                      '\ngoal',goal,
                                      '\nsbk',sbk.node,
                                      '\nlbk',lbk.node,
                                      '\nshort time',short_time,
                                      '\ndrive time',drive_time,
                                      '\ntt to long break',tt_fr_lbk,
                                      '\nsum',short_time + tt_fr_lbk,
                                      '\ntt to short break',tt_fr_sbk,
                                      '\nsum',short_time + tt_fr_sbk,
                                      '\nactual break hacky',actual_break,
                                      '\ntt to goal',tt_fr_goal,
                                      '\n',
                                      trip_chain
                                )
                                #ttidx = [fr,sbk.node,lbk.node,goal]
                                #print(time_matrix.loc[ttidx,ttidx])
                                #assert 0

                    else:
                        # print('lbk false',drive_time,tt_fr_goal,drive_time+tt_fr_goal)

                        if debug:
                            print('do not need long break, drive time + remaining is', drive_time + tt_fr_goal, 660)
                        if (short_time + tt_fr_goal >= 480):
                            if debug:
                                print('lbk false, sbk true',
                                      drive_time,tt_fr_goal,drive_time+tt_fr_goal,
                                      short_time,tt_fr_goal,short_time+tt_fr_goal)
                                print('will need short break, though',
                                      'short_time',short_time,
                                      'tt_fr_goal',tt_fr_goal,
                                      short_time + tt_fr_goal
                                )
                            # will need to take short break
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
                            print('did not take short break',sbk.node,
                                  'drive_time',drive_time,
                                  'fr_goal',tt_fr_goal,
                                  drive_time+tt_fr_goal,
                                  'short_time',short_time,
                                  short_time+tt_fr_goal)
                    if take_lbk:
                        trip_chain.append(lbk.node)
                        drive_time += tt_fr_lbk + lbk.drive_time_restore()
                        # never a case when long break not short break, so
                        short_time += tt_fr_lbk - (660 - 480) # hack
                        fr = lbk.node
                        if debug:
                            print('take long brk',lbk.node,short_time,drive_time)
                    tt_fr_goal = time_matrix.loc[fr,goal]
                    if np.isnan(tt_fr_goal):
                        print(fr,goal)
                        print(time_matrix.loc[:,[fr,goal]])
                        assert 0
                    brk_idx += 2

                # okay, done adding breaks, now what?
                if debug:
                    print('break_list',break_list,
                          'drive_time',drive_time,
                          'short_time',short_time,
                          'total_time',tt,
                          'brk_idx',brk_idx,
                          'tt remaining to goal',tt_fr_goal,
                          (drive_time + tt_fr_goal),
                          (short_time + tt_fr_goal),
                          '\n',
                          time_matrix.loc[trip_chain,trip_chain])


                # check if you need one more short break before goal
                if short_time + tt_fr_goal >= 480 :
                    sbk = breaks[brk_idx]
                    trip_chain.append(sbk.node)
                    tt_fr_sbk = time_matrix.loc[fr,sbk.node]
                    short_time += tt_fr_sbk + sbk.drive_time_restore()
                    drive_time += tt_fr_sbk
                    fr = sbk.node
                    tt_fr_goal = time_matrix.loc[fr,goal]
                    if debug:
                        print('slotting in one last short brk',sbk.node,short_time,drive_time)

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
        if debug:
            print(trip_chain) # before

            # check callback values too
            tt = 0
            tt_chain = []
            dt = 0
            dt_chain = []
            st = 0
            st_chain = []
            fr = 0
            for tcidx in trip_chain:
                tt += time_callback(manager.NodeToIndex(fr),
                                    manager.NodeToIndex(tcidx))
                dt += drive_callback(manager.NodeToIndex(fr),
                                     manager.NodeToIndex(tcidx))
                st += short_callback(manager.NodeToIndex(fr),
                                     manager.NodeToIndex(tcidx))
                tt_chain.append(tt)
                dt_chain.append(dt)
                st_chain.append(st)
                fr = tcidx
            print('travel time chain',tt_chain)
            print('drive time chain',dt_chain)
            print('short time chain',st_chain)

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

def initial_routes_no_breaks(demand,vehicles,time_matrix,
                   manager,time_callback,
                   debug=False):
    # initial routes should be a list of nodes to visit, in node space
    # (not solver index space, not map space)

    # assign one route per vehicle
    veh = 0
    prior = 0
    feasible_idx = demand.demand.feasible
    trip_chains = {}
    travel_times = {}

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
        travel_time = 0
        tt = 0
        while not reached_depot:

            if debug:
                print('loop',
                      'prior',prior,
                      'goal',goal)

            # considering trip from prior to goal
            # either insert a break node, or insert goal
            # what is travel time from prior to goal?
            tt_prior_goal = time_matrix.loc[prior,goal]
            if debug:
                print('go straight to goal',
                      'tt_prior_goal',tt_prior_goal,
                      'prior',prior,
                      'goal',goal,
                      'travel_time',travel_time)

            # just go straight to goal
            tt += time_callback(manager.NodeToIndex(prior),
                                manager.NodeToIndex(goal))
            travel_time += tt_prior_goal + demand.get_service_time(prior)

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
                          'travel_time',travel_time)
                assert tt+record.pickup_time  -1 <= record.depot_origin
                assert record.depot_origin <= tt+1 + record.pickup_time
            goal = next_goal

        if debug:
            print(trip_chain) # before

            # check callback values too
            tt = 0
            tt_chain = []
            fr = 0
            for tcidx in trip_chain:
                tt += time_callback(manager.NodeToIndex(fr),
                                    manager.NodeToIndex(tcidx))
                tt_chain.append(tt)
                fr = tcidx
            print('travel time chain',tt_chain)

        # loop to next demand, next trip chain, next vehicle
        trip_chains[veh] = trip_chain
        travel_times[veh] = travel_time
        veh += 1
        prior = 0
        travel_time = 0
    # print(time_matrix)
    print(trip_chains)
    print(travel_times)

    return trip_chains
