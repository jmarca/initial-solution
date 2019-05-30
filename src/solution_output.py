"""Solution output routines"""
from six.moves import xrange
from datetime import datetime, timedelta
import pandas as pd
import math
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
                   break_dim_floor,
                   args):  # pylint:disable=too-many-locals

    """Prints assignment on console"""
    # collect everything in a variable
    route_summary={}
    output_string = 'Objective: {}'.format(assignment.ObjectiveValue())
    # breaks are no longer break intervals
    # breaks = assignment.IntervalVarContainer()
    # for i in range(0,breaks.Size()):
    #     brk = breaks.Element(i)
    #     # print(brk)
    #     if (brk.StartMin()>=0 and brk.StartMin() < horizon * 10):
    #         print('break',i,'start',timedelta(minutes=brk.StartMin()),# '--',
    #               # timedelta(minutes=brk.StartMax()),
    #               'duration',timedelta(minutes=brk.DurationMin()),
    #               'end',timedelta(minutes=brk.EndMin())# ,'--',
    #               # timedelta(minutes=brk.EndMax())
    #         )
    #     else:
    #         print('break',i,'skipped--',
    #               'start',brk.StartMin(),
    #               'duration',brk.DurationMin(),
    #               'end',brk.EndMin())

    demand_served = {i:False for i in demand.demand.index}
    total_distance = 0
    total_travtime = 0
    total_load_served = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('cap')
    time_dimension = routing.GetDimensionOrDie('time')
    count_dimension = routing.GetDimensionOrDie('count')
    drive_dimension = False
    short_dimension = False
    if demand.break_nodes:
        drive_dimension = routing.GetDimensionOrDie('drive')
        short_dimension = routing.GetDimensionOrDie('break')
    output_string += '\nRoutes:\n'
    for vehicle in vehicles.vehicles:
        service_details = {}
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        previous_index = None
        plan_output  ='Route for vehicle {}:\n'.format(vehicle_id)
        distance = 0
        travtime = 0
        this_distance = 0
        this_time = 0
        link_time = 0
        pickups = 0
        lb_count = 0
        sb_count = 0
        while not routing.IsEnd(index):
            # load_var = capacity_dimension.CumulVar(index)

            time_var = time_dimension.CumulVar(index)
            load_var  = capacity_dimension.CumulVar(index)
            slack_var = time_dimension.SlackVar(index)
            visits_var  = count_dimension.CumulVar(index)
            node = manager.IndexToNode(index)
            node_demand = demand.get_demand(node)
            mapnode = demand.get_map_node(node)
            if mapnode < 0 and drive_dimension:
                # fill in with info about break type
                bn = demand.get_break_node(node)
                if bn.break_time == 600:
                    mapnode = '[10hr BRK]'
                    lb_count += 1
                if bn.break_time == 30:
                    mapnode = '[30min BRK]'
                    sb_count += 1
            else:
                mapnode = "mapnode {}".format(mapnode)

            load = assignment.Value(load_var)
            visits = assignment.Value(visits_var)
            min_time =  timedelta(minutes=assignment.Min(time_var))
            max_time =  timedelta(minutes=assignment.Max(time_var))
            slack_var_min = 0
            slack_var_max = 0
            if node_demand > 0:
                pickups += 1
                demand_index = demand.get_demand_number(node)
                demand_served[demand_index]=True
                # verify
                assert demand.demand.loc[demand_index]['origin']==node

                service_details[node-1]={'from':demand.demand.loc[node-1]['from_node'],
                                         'to':demand.demand.loc[node-1]['to_node']}

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
            travtime += link_time
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
            route_summary[vehicle_id] = {'vehicle_id':vehicle_id,
                                         'total_time':assignment.Value(time_var),
                                         'short_breaks':sb_count,
                                         'long_breaks':lb_count,
                                         'loads_served':service_details,
                                         'driving_distance':distance,
                                         'driving_time':travtime}
            assert math.isclose( distance/(args.speed/60), travtime, rel_tol=0.05)
            total_distance += distance
            total_travtime += travtime
            total_load_served += pickups
            total_time += assignment.Value(time_var)


        output_string += '\n'+plan_output+'\n'

    output_string +='\nTotal Distance of all routes: {0} miles'.format(total_distance)
    output_string +='\nTotal Loads picked up by all routes: {}'.format(total_load_served)
    output_string +='\nTotal Time of all routes: {0}'.format(timedelta(minutes=total_time))
    output_string +='\nTotal Travel Time of all routes: {0}'.format(timedelta(minutes=total_travtime))


    # output summary
    output_string += '\n\nRoute summaries'
    for entry in route_summary.items():
        (k,v) = entry
        load_numbers = [kkk  for kkk in v['loads_served'].keys()]
        load_numbers.sort()

        service_details = ["load {0}: {1} — {2}".format(kk+1,
                                                       v['loads_served'][kk]['from'],
                                                       v['loads_served'][kk]['to'])
                           for kk in load_numbers]

        service_summary = '; '.join(service_details)

        output_string += """
\nRoute: {0},
Driving time: {1} min,
30 min breaks: {2},
10 hr breaks: {3},
Total route time: {4} min
Total distance driven: {5} mi
Loads: {6}
""".format(v['vehicle_id'],
           int(v['driving_time']),
           v['short_breaks'],
           v['long_breaks'],
           int(v['total_time']),
           int(v['driving_distance']),
           service_summary)

    # print unserved but feasible demands
    skipped_demands = ''
    infeasible_demands = ''
    for entry in demand_served.items():
        (k,v) = entry
        if not v:
            d = demand.demand.loc[entry[0]]
            if d.feasible:
                skipped_demands += "\n{}: from {} to {}".format(entry[0]+1,d.from_node,d.to_node)
            else:
                infeasible_demands += "\n{}: from {} to {}, {}".format(entry[0]+1,d.from_node,d.to_node,d.constraint)
    if skipped_demands != '':
        output_string += '\n\nDemands that are not served:'
        output_string += skipped_demands

    # print gimpy demands
    if infeasible_demands != '':
        output_string +='\n\nDemands that are infeasible:'
        output_string += infeasible_demands

    if args.summary_output:
        # possible collision
        idx = 1
        checkname = args.summary_output
        while os.path.exists(checkname):
            checkname = re.sub(r"\.(.*)$",r"_{}.\1".format(idx),args.summary_output)
            idx += 1

        f = open(checkname, 'a+')
        print(output_string,file=f,flush=True)
        f.close()
    else:

        print(output_string)


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
    total_travtime = 0
    total_load_served = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('cap')
    time_dimension = routing.GetDimensionOrDie('time')
    count_dimension = routing.GetDimensionOrDie('count')
    for vehicle in vehicles.vehicles:
        this_vehicle_rows=[]
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        distance = 0
        travtime = 0
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
            travtime += this_time

        # done with loop, have returned to depot
        load_var = capacity_dimension.CumulVar(index)
        visits_var  = count_dimension.CumulVar(index)
        time_var = time_dimension.CumulVar(index)
        slack_var = time_dimension.SlackVar(index)
        visits = assignment.Value(visits_var)
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
    total_travtime = 0
    total_load_served = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('cap')
    time_dimension = routing.GetDimensionOrDie('time')
    count_dimension = routing.GetDimensionOrDie('count')
    for vehicle in vehicles.vehicles:
        this_vehicle_rows=[]
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        distance = 0
        travtime = 0
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
            travtime += this_time

        # done with loop, have returned to depot
        load_var = capacity_dimension.CumulVar(index)
        visits_var  = count_dimension.CumulVar(index)
        time_var = time_dimension.CumulVar(index)
        slack_var = time_dimension.SlackVar(index)
        visits = assignment.Value(visits_var)
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
