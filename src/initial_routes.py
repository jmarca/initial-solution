import pandas as pd
import numpy as np
import itertools
import read_csv as reader
import breaks
import sys
import math

"""Functions for setting up intial routes"""

def initial_routes(demand,vehicles,time_matrix,
                   manager,time_callback,drive_callback):#,time_callback,drive_callback):
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
        goal = record.origin
        tt = 0
        dt = 0
        travel_time = 0
        drive_time  = 0
        # print('before',travel_time,drive_time)
        while not reached_depot:
            # if nextnode to goal is < 660, move on, otherwise loop to next break
            # grab break nodes from prior to goal
            from_filter = time_matrix.loc[prior,:].apply(lambda a: not np.isnan(a))
            to_filter   = time_matrix.loc[:,goal].apply(lambda a: not np.isnan(a))
            local_df = time_matrix.loc[from_filter & to_filter,from_filter & to_filter]
            if (drive_time + local_df.loc[prior,goal] < 660):
                tt += time_callback(manager.NodeToIndex(prior),
                                    manager.NodeToIndex(goal))
                dt += drive_callback(manager.NodeToIndex(prior),
                                     manager.NodeToIndex(goal))
                dest_demand = demand.get_demand(goal)
                origin_demand = demand.get_demand(prior)
                travel_to_goal =  math.floor(time_matrix.loc[prior,goal])
                if(dest_demand == 0):
                    if goal > 0:
                        # not depot node
                        drive_time += travel_to_goal-660
                    else:
                        # depot node
                        drive_time += travel_to_goal
                else:
                    drive_time += travel_to_goal

                if origin_demand == 0:
                    if prior > 0:
                        travel_time += travel_to_goal + 600 # break time at prior
                    else:
                        # came from depot
                        travel_time += travel_to_goal
                else:
                    # pickup or delivery at prior
                    if origin_demand > 0:
                        travel_time += travel_to_goal + record.pickup_time
                    else:
                        travel_time += travel_to_goal + record.dropoff_time

                #print(travel_time,tt,drive_time,dt,'from',prior,'to',goal)
                assert int(travel_time) == tt
                assert math.floor(drive_time) == dt

                if goal == 0:
                    # don't append depot to trip chain
                    # loop to next demand record
                    reached_depot = True
                else:
                    trip_chain.append(goal)
                    prior = trip_chain[-1]
                    # cycle goal forward
                    if goal == record.origin:
                        # check that time window requirements are satisfied
                        # print(record.from_node,record.origin,record.early,tt,record.late)
                        assert tt-1 <= record.depot_origin
                        assert record.depot_origin <= tt+1

                    if goal == record.destination:
                        goal = 0
                    else:
                        goal = record.destination
                # print('reached',goal)
            else:
                # trip to goal is not short enough, use a break node

                # find the cheapest link from prior
                minval = local_df[local_df>0].min()
                ismin = local_df.loc[prior,:] == minval
                nextnode = local_df.loc[prior,ismin].index[0]
                trip_chain.append(nextnode)

                # print(travel_time,tt,drive_time,dt,'from',prior,'to',trip_chain[-1])
                # track travel time
                tt += time_callback(manager.NodeToIndex(prior),
                                    manager.NodeToIndex(nextnode))
                dt += drive_callback(manager.NodeToIndex(prior),
                                     manager.NodeToIndex(nextnode))
                travel_to_nextnode = math.floor(time_matrix.loc[prior,nextnode])
                dest_demand = demand.get_demand(nextnode)
                if(dest_demand == 0):
                    if (nextnode > 0):
                        drive_time += travel_to_nextnode - 660
                    else:
                        # depot node
                        drive_time += travel_to_nextnode
                else:
                    drive_time += travel_to_nextnode

                # break time modeled as transit time at origin node
                origin_demand = demand.get_demand(prior)

                if(origin_demand == 0):
                    if (prior > 0):
                        travel_time += travel_to_nextnode + 600 # break time
                    else:
                        # coming from depot
                        travel_time += travel_to_nextnode
                else:
                    # pickup, delivery time modeled as transit time at prior node
                    if origin_demand > 0:
                        travel_time += travel_to_nextnode + record.pickup_time
                    else:
                        travel_time += travel_to_nextnode + record.dropoff_time

                # print(travel_time,tt,drive_time,dt,'from',prior,'to',trip_chain[-1])
                assert int(travel_time) == tt
                assert math.floor(drive_time) == dt
                prior = trip_chain[-1]


        # print(trip_chain)
        # loop to next demand, next trip chain, next vehicle
        trip_chains[veh] = trip_chain
        travel_times[veh] = travel_time
        drive_times[veh] = drive_time
        veh += 1
        prior = 0
        travel_time = 0
        drive_time = 0

    print(trip_chains)
    # print(travel_times)
    # print(drive_times)
    return trip_chains
