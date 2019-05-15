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
                   manager,time_callback,drive_callback,
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
        # print('before',travel_time,drive_time)
        while not reached_depot:

            # considering trip from prior to goal
            # either insert a break node, or insert goal
            # what is travel time from prior to goal?
            tt_prior_goal = time_matrix.loc[prior,goal]

            if drive_time + tt_prior_goal < 660:

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
                        print(record,'\n','tt',tt,'travel_time',travel_time,'dt',dt,'drive_time',drive_time)
                    assert tt+record.pickup_time  -1 <= record.depot_origin
                    assert record.depot_origin <= tt+1 + record.pickup_time
                goal = next_goal
                continue
            else:
                # cannot go straight from prior to goal.  Must go to at least one break

                break_list = demand.get_break_node_chain(prior,goal)
                if debug:
                    print(break_list)
                if break_list == None:
                    print('missing break list for',prior,goal)
                    assert 0
                # fr keeps track of "from" break node
                fr = prior
                brk_idx = 0
                node = break_list[brk_idx]
                while node in break_list:
                    tt_fr_node = time_matrix.loc[fr,node]
                    tt_node_goal = time_matrix.loc[node,goal]

                    # in the zeroth case, must visit this break node, so append it
                    trip_chain.append(node)
                    brk_idx += 1
                    # compute travel time, drive time
                    bn = demand.get_break_node(node)

                    # do we need to visit another break?
                    if drive_time + tt_fr_node + bn.drive_time_restore() +tt_node_goal < 660:
                        # will not need another break
                        # account for getting to and taking this break

                        travel_time += demand.get_service_time(fr) # pickup or dropoff
                        travel_time += tt_fr_node    # travel
                        travel_time += bn.break_time # take a break
                        # ditto drive time
                        drive_time += tt_fr_node              # travel
                        drive_time += bn.drive_time_restore() # break reset the clock

                        # account for remaining travel to goal
                        travel_time += tt_node_goal  # travel to goal, no more breaks
                        drive_time += tt_node_goal   # travel to goal, no more breaks

                        tt += time_callback(manager.NodeToIndex(fr),
                                            manager.NodeToIndex(node))
                        tt += time_callback(manager.NodeToIndex(node),
                                            manager.NodeToIndex(goal))
                        dt += drive_callback(manager.NodeToIndex(fr),
                                             manager.NodeToIndex(node))
                        dt += drive_callback(manager.NodeToIndex(node),
                                             manager.NodeToIndex(goal))


                        # keep an eye on things
                        if debug:
                            print ('can reach goal with no more breaks\n',
                                   'brk_idx',brk_idx,'of',len(break_list),
                                   'tt_fr_node',tt_fr_node,
                                   'tt_node_goal',tt_node_goal,
                                   'prior',prior,
                                   'goal',goal,
                                   'from break',fr,
                                   'break node',node,
                                   'dt',dt,
                                   'drive_time',drive_time,
                                   'tt',tt,
                                   'travel_time',travel_time,'\n',record)

                        assert int(dt) == int(drive_time)
                        assert int(tt) == int(travel_time)
                        next_goal = cycler(goal)
                        reached_depot = next_goal == -1
                        if not reached_depot:
                            trip_chain.append(goal)
                            prior = goal
                            goal = next_goal
                        node = -1
                    else:
                        # will need to visit another break node
                        # account for getting to and taking this break

                        travel_time += demand.get_service_time(fr) # pickup or dropoff
                        travel_time += tt_fr_node    # travel
                        # ditto drive time
                        drive_time += tt_fr_node              # travel
                        tt += time_callback(manager.NodeToIndex(fr),
                                            manager.NodeToIndex(node))
                        dt += drive_callback(manager.NodeToIndex(fr),
                                             manager.NodeToIndex(node))
                        if debug:
                            print ('cannot reach goal, need another break\n',
                                   'brk_idx',brk_idx,'of',len(break_list),
                                   'tt_fr_node',tt_fr_node,
                                   'tt_node_goal',tt_node_goal,
                                   'prior',prior,
                                   'goal',goal,
                                   'from break',fr,
                                   'break node',node,
                                   'dt',dt,
                                   'drive_time',drive_time,
                                   'tt',tt,
                                   'travel_time',travel_time,'\n',record)
                        # actually, the following asserts are not true
                        # because this logic is out of sync...the
                        # transit at the break node is already
                        # accounted for at this time
                        assert int(dt) == int(drive_time)
                        assert int(tt) == int(travel_time)

                        # so now add in the transit of the break node
                        travel_time += bn.break_time # take a break
                        drive_time += bn.drive_time_restore() # break reset the clock

                        # loop
                        fr = node
                        node = break_list[brk_idx]

            # # if nextnode to goal is < 660, move on, otherwise loop to next break
            # # grab break nodes from prior to goal
            # from_filter = time_matrix.loc[prior,:].apply(lambda a: not np.isnan(a))
            # to_filter   = time_matrix.loc[:,goal].apply(lambda a: not np.isnan(a))
            # local_df = time_matrix.loc[from_filter & to_filter,from_filter & to_filter]
            # travel_to_goal =  math.floor(time_matrix.loc[prior,goal])
            # # if debug:
            # #     print('prior',prior,'goal',goal,'\n',local_df)
            # if (drive_time + travel_to_goal < 660):
            #     if debug:
            #         print('drive time plus travel less than 660')
            #     tt += time_callback(manager.NodeToIndex(prior),
            #                         manager.NodeToIndex(goal))
            #     dt += drive_callback(manager.NodeToIndex(prior),
            #                          manager.NodeToIndex(goal))
            #     dest_demand = demand.get_demand(goal)
            #     origin_demand = demand.get_demand(prior)
            #     # if(dest_demand == 0):
            #     #     if goal > 0:
            #     #         # not depot node
            #     #         drive_time += travel_to_goal-660
            #     #     else:
            #     #         # depot node
            #     #         drive_time += travel_to_goal
            #     # else:
            #     #     drive_time += travel_to_goal

            #     if origin_demand == 0:
            #         if prior > 0:
            #             travel_time += travel_to_goal + 600 # break time at prior
            #             drive_time += travel_to_goal-660
            #         else:
            #             # came from depot
            #             travel_time += travel_to_goal
            #             drive_time += travel_to_goal
            #     else:
            #         drive_time += travel_to_goal
            #         # pickup or delivery at prior
            #         if origin_demand > 0:
            #             travel_time += travel_to_goal + record.pickup_time
            #         else:
            #             travel_time += travel_to_goal + record.dropoff_time

            #     if debug:
            #         print(travel_time,tt,drive_time,dt,'from',prior,'to',goal)
            #     assert int(travel_time) == tt
            #     assert math.floor(drive_time) == dt

            #     if debug:
            #         print('reached',goal)
            #     if goal == 0:
            #         # don't append depot to trip chain
            #         # loop to next demand record
            #         reached_depot = True
            #     else:
            #         trip_chain.append(goal)
            #         prior = trip_chain[-1]
            #         # cycle goal forward
            #         if goal == record.origin:
            #             # check that time window requirements are satisfied
            #             # print(record.from_node,record.origin,record.early,tt,record.late)
            #             if (tt+record.pickup_time -1 > record.depot_origin or
            #                 record.depot_origin > tt+1 + record.pickup_time):
            #                 print(record,'\n',tt,travel_time,dt,drive_time)
            #             assert tt  + record.pickup_time -1 <= record.depot_origin
            #             assert record.depot_origin <= tt+1  + record.pickup_time

            #         if goal == record.destination:
            #             goal = 0
            #         else:
            #             goal = record.destination

            # else:
            #     if debug:
            #         print('drive time plus travel to goal greater than 660')
            #     # trip to goal is not short enough, use a break node
            #     # remove goal from local_df so we don't get confused
            #     #to_filter[goal] = False
            #     local_df = time_matrix.loc[from_filter & to_filter,from_filter & to_filter]

            #     # if debug:
            #     #     print('prior',prior,'goal',goal,'\n',local_df)
            #     # find the cheapest link from prior
            #     minval = local_df[local_df>0].min()
            #     ismin = local_df.loc[prior,:] == minval
            #     # if debug:
            #     #     print(minval, '\n',ismin )
            #     nextnode = local_df.loc[prior,ismin].index[0]
            #     trip_chain.append(nextnode)

            #     if debug:
            #         print(travel_time,tt,drive_time,dt,'from',prior,'to',trip_chain[-1])
            #     # track travel time
            #     tt += time_callback(manager.NodeToIndex(prior),
            #                         manager.NodeToIndex(nextnode))
            #     dt += drive_callback(manager.NodeToIndex(prior),
            #                          manager.NodeToIndex(nextnode))
            #     travel_to_nextnode = math.floor(time_matrix.loc[prior,nextnode])
            #     dest_demand = demand.get_demand(nextnode)
            #     # if(dest_demand == 0):
            #     #     if (nextnode > 0):
            #     #         drive_time += travel_to_nextnode - 660
            #     #     else:
            #     #         # depot node
            #     #         drive_time += travel_to_nextnode
            #     # else:
            #     #     drive_time += travel_to_nextnode

            #     # break time modeled as transit time at origin node
            #     origin_demand = demand.get_demand(prior)

            #     if(origin_demand == 0):
            #         if (prior > 0):
            #             travel_time += travel_to_nextnode + 600 # break time
            #             drive_time += travel_to_nextnode - 660
            #         else:
            #             # coming from depot
            #             travel_time += travel_to_nextnode
            #             drive_time += travel_to_nextnode
            #     else:
            #         drive_time += travel_to_nextnode
            #         # pickup, delivery time modeled as transit time at prior node
            #         if origin_demand > 0:
            #             travel_time += travel_to_nextnode + record.pickup_time
            #         else:
            #             travel_time += travel_to_nextnode + record.dropoff_time
            #     if math.floor(drive_time) != dt:
            #         print(travel_time,tt,drive_time,dt,'from',prior,'to',trip_chain[-1])
            #     assert int(travel_time) == tt
            #     assert math.floor(drive_time) == dt
            #     prior = trip_chain[-1]


        print(trip_chain)
        # loop to next demand, next trip chain, next vehicle
        trip_chains[veh] = trip_chain
        travel_times[veh] = travel_time
        drive_times[veh] = drive_time
        veh += 1
        prior = 0
        travel_time = 0
        drive_time = 0

    # print(trip_chains)
    # print(travel_times)
    # print(drive_times)
    return trip_chains
