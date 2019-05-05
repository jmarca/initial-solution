"""Solution output routines"""
from six.moves import xrange
from datetime import datetime, timedelta

# copied from Google v7.0 example
def print_solution(demand,
                   dist_callback,
                   vehicles,
                   manager,
                   routing,
                   assignment,
                   horizon):  # pylint:disable=too-many-locals
    """Prints assignment on console"""
    print('Objective: {}'.format(assignment.ObjectiveValue()))
    print('Breaks:')
    breaks = assignment.IntervalVarContainer()
    for i in range(0,breaks.Size()):
        brk = breaks.Element(i)
        # print(brk)
        if (brk.StartMin()>0 ):
            print('start',timedelta(minutes=brk.StartMin()),# '--',
                  # timedelta(minutes=brk.StartMax()),
                  'duration',timedelta(minutes=brk.DurationMin()),
                  'end',timedelta(minutes=brk.EndMin())# ,'--',
                  # timedelta(minutes=brk.EndMax())
            )
        else:
            print('break',i,'skipped--',
                  'start',timedelta(minutes=brk.StartMin()),
                  'duration',timedelta(minutes=brk.DurationMin()),
                  'end',timedelta(minutes=brk.EndMin()))


    total_distance = 0
    total_load_served = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')
    time_dimension = routing.GetDimensionOrDie('Time')
    print('Routes:')
    for vehicle in vehicles.vehicles:
        vehicle_id = vehicle.index
        index = routing.Start(vehicle_id)
        plan_output  ='Route for vehicle {}:\n'.format(vehicle_id)
        distance = 0
        this_distance = 0
        this_time = 0
        pickups = 0
        while not routing.IsEnd(index):
            # load_var = capacity_dimension.CumulVar(index)

            time_var = time_dimension.CumulVar(index)
            load_var  = capacity_dimension.CumulVar(index)
            slack_var = time_dimension.SlackVar(index)

            node = manager.IndexToNode(index)
            mapnode = demand.get_map_node(node)
            load = assignment.Value(load_var)
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

            plan_output += 'node {0}, mapnode {1}, Load {2},  Time({3},{4}) Slack({5},{6}) Link time({7}) Link distance({8} mi)\n ->'.format(
                node,
                mapnode,
                load,
                min_time,
                max_time,
                slack_var_min,
                slack_var_max,
                timedelta(minutes=this_time),
                this_distance
            )
            previous_index = index
            index = assignment.Value(routing.NextVar(index))

            this_time = routing.GetArcCostForVehicle(previous_index, index,
                                                     vehicle_id)
            this_distance = dist_callback(previous_index,index)
            distance += this_distance
        load_var = capacity_dimension.CumulVar(index)
        time_var = time_dimension.CumulVar(index)
        slack_var = time_dimension.SlackVar(index)
        plan_output += ' {0} Load({1})  Time({2},{3})  Link time({4}) Link distance({5} mi)\n'.format(
            manager.IndexToNode(index),
            assignment.Value(load_var),
            timedelta(minutes=assignment.Min(time_var)),
            timedelta(minutes=assignment.Max(time_var)),
            timedelta(minutes=this_time),
            this_distance
        )
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
