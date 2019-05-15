"""Solution output routines"""
from six.moves import xrange
from datetime import datetime, timedelta
import pandas as pd
import os
import re

def print_initial_solution(demand,
                           dist_matrix,
                           time_matrix,
                           vehicles,
                           manager,
                           routing,
                           assignment,
                           horizon):
    max_route_time = 0
    for vehicle in vehicles.vehicles:
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_time = 0
        while not routing.IsEnd(index):
            plan_output += ' {} -> '.format(manager.IndexToNode(index))
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            route_time += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        plan_output += '{}\n'.format(manager.IndexToNode(index))
        plan_output += 'Time of the route: {}\n'.format(timedelta(minutes=route_time))
        print(plan_output)
        max_route_time = max(route_time, max_route_time)
    print('Maximum of the route times: {}m'.format(timedelta(minutes=max_route_time)))



# heavily modified from Google v7.0 example
def print_solution(demand,
                   dist_matrix,
                   time_matrix,
                   vehicles,
                   manager,
                   routing,
                   assignment,
                   horizon,
                   break_dim_floor):  # pylint:disable=too-many-locals
    """Prints assignment on console"""
    print('Objective: {}'.format(assignment.ObjectiveValue()))
    print('Breaks:')
    breaks = assignment.IntervalVarContainer()
    for i in range(0,breaks.Size()):
        brk = breaks.Element(i)
        # print(brk)
        if (brk.StartMin()>=0 and brk.StartMin() < horizon * 10):
            print('break',i,'start',timedelta(minutes=brk.StartMin()),# '--',
                  # timedelta(minutes=brk.StartMax()),
                  'duration',timedelta(minutes=brk.DurationMin()),
                  'end',timedelta(minutes=brk.EndMin())# ,'--',
                  # timedelta(minutes=brk.EndMax())
            )
        else:
            print('break',i,'skipped--',
                  'start',brk.StartMin(),
                  'duration',brk.DurationMin(),
                  'end',brk.EndMin())

    total_distance = 0
    total_load_served = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')
    time_dimension = routing.GetDimensionOrDie('Time')
    count_dimension = routing.GetDimensionOrDie('Count')
    drive_dimension = False
    short_dimension = False
    if len(demand.break_nodes.keys()) > 0:
        drive_dimension = routing.GetDimensionOrDie('Drive')
        short_dimension = routing.GetDimensionOrDie('Short Break')

    print('Routes:')
    for vehicle in vehicles.vehicles:
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        plan_output  ='Route for vehicle {}:\n'.format(vehicle_id)
        distance = 0
        this_distance = 0
        this_time = 0
        link_time = 0
        pickups = 0
        while not routing.IsEnd(index):
            # load_var = capacity_dimension.CumulVar(index)

            time_var = time_dimension.CumulVar(index)
            load_var  = capacity_dimension.CumulVar(index)
            slack_var = time_dimension.SlackVar(index)
            visits_var  = count_dimension.CumulVar(index)

            node = manager.IndexToNode(index)
            mapnode = demand.get_map_node(node)
            if mapnode < 0 and drive_dimension:
                # fill in with info about break type
                bn = demand.get_break_node(node)
                if bn.break_time == 600:
                    mapnode = '[10hr BRK]'
                if bn.break_time == 30:
                    mapnode = '[30min BRK]'
            else:
                mapnode = "mapnode {}".format(mapnode)

            load = assignment.Value(load_var)
            visits = assignment.Value(visits_var)
            min_time =  timedelta(minutes=assignment.Min(time_var))
            max_time =  timedelta(minutes=assignment.Max(time_var))
            slack_var_min = 0
            slack_var_max = 0
            node_demand = demand.get_demand(node)
            if node_demand > 0:
                pickups += 1
            # at this point, everything should have slack var
            slack_var_min = timedelta(minutes=assignment.Min(slack_var))
            slack_var_max = timedelta(minutes=assignment.Max(slack_var))
            if drive_dimension:
                drive_var = drive_dimension.CumulVar(index)
                drive_time = assignment.Value(drive_var)
                short_var = short_dimension.CumulVar(index)
                short_time = assignment.Value(short_var)
                plan_output += 'node {0}, {1}, Load {2}, 10hr Break Time {3}, 30min Break Time {12},  Arrive Time({4},{5}), Elapsed Time({8}),  Link: (Time {10}, Dist {9} mi), visits: {11}\n ->'.format(
                    node,
                    mapnode,
                    load,
                    timedelta(minutes=(drive_time-break_dim_floor)),
                    min_time,
                    max_time,
                    slack_var_min,
                    slack_var_max,
                    timedelta(minutes=this_time),
                    this_distance,
                    timedelta(minutes=link_time),
                    visits,
                    timedelta(minutes=(short_time-break_dim_floor))
                )
            else:
                plan_output += 'node {0}, {1}, Load {2},  Time({3},{4}) Slack({5},{6}) Time({7}) Link (Time {9}, distance {8} mi),visits: {10}\n ->'.format(
                    node,
                    mapnode,
                    load,
                    min_time,
                    max_time,
                    slack_var_min,
                    slack_var_max,
                    timedelta(minutes=this_time),
                    this_distance,
                    timedelta(minutes=link_time),
                    visits
                )

            previous_index = index
            index = assignment.Value(routing.NextVar(index))

            this_time = routing.GetArcCostForVehicle(previous_index, index,
                                                     vehicle_id)
            this_distance = int(dist_matrix.loc[manager.IndexToNode(previous_index),
                                                manager.IndexToNode(index)])
            link_time = int(time_matrix.loc[manager.IndexToNode(previous_index),
                                            manager.IndexToNode(index)])
            distance += this_distance
        load_var = capacity_dimension.CumulVar(index)
        visits_var  = count_dimension.CumulVar(index)
        time_var = time_dimension.CumulVar(index)
        slack_var = time_dimension.SlackVar(index)
        visits = assignment.Value(visits_var)
        if drive_dimension:
            drive_var = drive_dimension.CumulVar(index)
            drive_time = assignment.Value(drive_var)
            short_var = short_dimension.CumulVar(index)
            short_time = assignment.Value(short_var)
            plan_output += 'End:{0}, Load({1}), 10hr Break Time {7}, 30min Break Time {8},  Time({2},{3})  Elapsed time({4}) Link:(Time {9}, Dist {5} mi), visits {6}\n'.format(
                manager.IndexToNode(index),
                assignment.Value(load_var),
                timedelta(minutes=assignment.Min(time_var)),
                timedelta(minutes=assignment.Max(time_var)),
                timedelta(minutes=this_time),
                this_distance,
                visits,
                timedelta(minutes=(drive_time-break_dim_floor)),
                timedelta(minutes=(short_time-break_dim_floor)),
                timedelta(minutes=link_time)
            )

        else:
            plan_output += ' {0} Load({1})  Time({2},{3})  Link time({4}) Link distance({5} mi), visits {6}\n'.format(
                manager.IndexToNode(index),
                assignment.Value(load_var),
                timedelta(minutes=assignment.Min(time_var)),
                timedelta(minutes=assignment.Max(time_var)),
                timedelta(minutes=this_time),
                this_distance,
                visits
            )
        # if vehicle does nothing, don't print depot to depot
        if visits < 2:
            plan_output  ='Route for vehicle {}: unused'.format(vehicle_id)
        else:
            plan_output += 'Distance of the route: {0} miles\n'.format(distance)
            plan_output += 'Loads served by route: {}\n'.format(
                pickups)
            plan_output += 'Time of the route: {}\n'.format(
                timedelta(minutes=assignment.Value(time_var)))
        print(plan_output)
        total_distance += distance
        total_load_served += pickups
        total_time += assignment.Value(time_var)
    print('Total Distance of all routes: {0} miles'.format(total_distance))
    print('Total Loads picked up by all routes: {}'.format(total_load_served))
    print('Total Time of all routes: {0}'.format(timedelta(minutes=total_time)))

    # print gimpy demands

    infeasible_index = ~demand.demand.feasible
    if len(infeasible_index[infeasible_index]) > 0:
        print('\nDemands that are infeasible:')
        for idx in demand.demand.index[infeasible_index]:
            d = demand.demand.loc[idx]
            print(d.constraint)

def csv_output(demand,
               dist_matrix,
               time_matrix,
               vehicles,
               manager,
               routing,
               assignment,
               horizon,
               basename):

    # First up, handle the Routes output.
    # For each route, dump each pickup dropoff event in a list
    vcsv = []

    total_distance = 0
    total_load_served = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')
    time_dimension = routing.GetDimensionOrDie('Time')
    count_dimension = routing.GetDimensionOrDie('Count')
    drive_dimension = routing.GetDimensionOrDie('Drive')
    for vehicle in vehicles.vehicles:
        this_vehicle_rows=[]
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        distance = 0
        this_distance = 0
        this_time = 0
        link_time = 0
        pickups = 0
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            load_var  = capacity_dimension.CumulVar(index)
            slack_var = time_dimension.SlackVar(index)
            visits_var  = count_dimension.CumulVar(index)

            node = manager.IndexToNode(index)
            mapnode = demand.get_map_node(node)
            load = assignment.Value(load_var)
            visits = assignment.Value(visits_var)
            min_time =  assignment.Min(time_var)
            max_time =  assignment.Max(time_var)
            slack_var_min = 0
            slack_var_max = 0
            node_demand = demand.get_demand(node)
            drive_var = drive_dimension.CumulVar(index)
            drive_time = assignment.Value(drive_var)
            row = {'location':mapnode,
                   'demand':node_demand,
                   'order':visits,
                   'time':assignment.Value(time_var),
                   'distance':this_distance,
                   'veh':vehicle_id}

            this_vehicle_rows.append(row)
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            this_time = routing.GetArcCostForVehicle(previous_index, index,
                                                     vehicle_id)
            this_distance = int(dist_matrix.loc[manager.IndexToNode(previous_index),
                                                manager.IndexToNode(index)])
            link_time = int(time_matrix.loc[manager.IndexToNode(previous_index),
                                            manager.IndexToNode(index)])
            distance += this_distance

        # done with loop, have returned to depot
        load_var = capacity_dimension.CumulVar(index)
        visits_var  = count_dimension.CumulVar(index)
        time_var = time_dimension.CumulVar(index)
        slack_var = time_dimension.SlackVar(index)
        visits = assignment.Value(visits_var)
        drive_var = drive_dimension.CumulVar(index)
        drive_time = assignment.Value(drive_var)
        node = manager.IndexToNode(index)
        mapnode = demand.get_map_node(node)

        row = {'location':mapnode,
               'demand':0,
               'order':visits,
               'time':assignment.Value(time_var),
               'distance':this_distance,
               'veh':vehicle_id}
        this_vehicle_rows.append(row)
        if visits>1:
            vcsv.extend(this_vehicle_rows)



    # now save to csv
    dump_obj = pd.DataFrame(vcsv)
    # check for any existing file
    idx = 1

    checkname = basename
    match = re.search(r"\.csv", checkname)
    if not match:
        print ('no match',basename)
        basename += ".csv"

    checkname = basename
    while os.path.exists(checkname):
        checkname = re.sub(r"\.csv","_{}.csv".format(idx),basename)
        idx += 1
        # or just get rid of it
        # os.unlink(basename+"_assignments.csv")

    dump_obj.to_csv(checkname, index=False)


def csv_demand_output(demand,
                      dist_matrix,
                      time_matrix,
                      vehicles,
                      manager,
                      routing,
                      assignment,
                      horizon,
                      basename):

    # First up, handle the Routes output.
    # For each route, dump each pickup dropoff event in a list
    demand_details = {}

    total_distance = 0
    total_load_served = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')
    time_dimension = routing.GetDimensionOrDie('Time')
    count_dimension = routing.GetDimensionOrDie('Count')
    drive_dimension = routing.GetDimensionOrDie('Drive')
    for vehicle in vehicles.vehicles:
        this_vehicle_rows=[]
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        distance = 0
        this_distance = 0
        this_time = 0
        link_time = 0
        pickups = 0
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            load_var  = capacity_dimension.CumulVar(index)
            slack_var = time_dimension.SlackVar(index)
            visits_var  = count_dimension.CumulVar(index)

            node = manager.IndexToNode(index)
            mapnode = demand.get_map_node(node)
            load = assignment.Value(load_var)
            visits = assignment.Value(visits_var)
            min_time =  assignment.Min(time_var)
            max_time =  assignment.Max(time_var)
            slack_var_min = 0
            slack_var_max = 0
            node_demand = demand.get_demand(node)
            drive_var = drive_dimension.CumulVar(index)
            drive_time = assignment.Value(drive_var)

            if node_demand != 0:
                if node_demand > 0:
                    # pickup
                    row = {'pickup_node':mapnode,
                           'pickup_order':visits,
                           'pickup_time':assignment.Value(time_var),
                           'pickup_distance':this_distance,
                           'veh':vehicle_id}
                    demand_details[node] = row
                if node_demand < 0:
                    # pickup
                    row = {'dropoff_node':mapnode,
                           'dropoff_order':visits,
                           'dropoff_time':assignment.Value(time_var),
                           'dropoff_distance':this_distance,
                           'veh':vehicle_id}
                    demand_details[node] = row

            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            this_time = routing.GetArcCostForVehicle(previous_index, index,
                                                     vehicle_id)
            this_distance = int(dist_matrix.loc[manager.IndexToNode(previous_index),
                                                manager.IndexToNode(index)])
            link_time = int(time_matrix.loc[manager.IndexToNode(previous_index),
                                            manager.IndexToNode(index)])
            distance += this_distance

        # done with loop, have returned to depot
        load_var = capacity_dimension.CumulVar(index)
        visits_var  = count_dimension.CumulVar(index)
        time_var = time_dimension.CumulVar(index)
        slack_var = time_dimension.SlackVar(index)
        visits = assignment.Value(visits_var)
        drive_var = drive_dimension.CumulVar(index)
        drive_time = assignment.Value(drive_var)
        node = manager.IndexToNode(index)
        mapnode = demand.get_map_node(node)

    # now cycle over demands, create output records
    rows = []

    for didx in demand.demand.index:
        d = demand.demand.loc[didx]

        if d.origin in demand_details:
            row = {}
            for entry in demand_details[d.origin].items():
                row[entry[0]]=entry[1]
            for entry in demand_details[d.destination].items():
                row[entry[0]]=entry[1]
            rows.append(row)
        else:
            # demand not served
            row = {'pickup_node':d.from_node,
                   'dropoff_node':d.to_node,
                   'pickup_order':-1,
                   'pickup_time':0,
                   'pickup_distance':0,
                   'dropoff_order':-1,
                   'dropoff_time':0,
                   'dropoff_distance':0,
                   'veh':-1}
            rows.append(row)

    # now save to csv
    dump_obj = pd.DataFrame(rows)
    # check for any existing file
    idx = 1

    checkname = basename
    match = re.search(r"\.csv", checkname)
    if not match:
        print ('no match',basename)
        basename += ".csv"

    checkname = basename
    while os.path.exists(checkname):
        checkname = re.sub(r"\.csv","_{}.csv".format(idx),basename)
        idx += 1

    dump_obj.to_csv(checkname, index=False)
