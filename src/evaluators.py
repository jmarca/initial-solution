# create simple 2D array for distance lookup?
# Define cost of each arc.
import numpy as np

def create_demand_callback(demand):
    """ create a callback function for demand """
    _demand = {}
    # if node supplied is not one of the O D nodes, return 0 for demand
    for idx in demand.demand.index:
        record = demand.demand.loc[idx]
        # from node has 1 supply, to node has -1 demand
        _demand[record.origin]=int(1)
        _demand[record.destination]=int(-1)

    def demand_callback(manager, index):
        """Returns the demand at the index, if defined, or zero."""
        # Convert from routing variable Index to demand array Node.
        node = manager.IndexToNode(index)
        if node in _demand:
            return _demand[node]
        return int(0)

    # return the callback, which will need to be set up with partial
    return demand_callback


def create_time_callback(travel_minutes_matrix,
                         demand):
    """ create a callback function for time """

    # preprocess travel and service time to speed up solver
    _total_time = {}
    depot_list = np.array([0]) # hack---will fail when depots is not just node 0
    node_list = np.append(depot_list,demand.get_node_list())
    for from_node in node_list:
        _total_time[from_node] = {}
        mapnode_from = 0
        service_time = 0
        if (from_node>0):
            mapnode_from = demand.get_map_node(from_node)
            service_time = demand.get_service_time(from_node)
        for to_node in node_list:
            if from_node == to_node:
                _total_time[from_node][to_node] = 0
            else:
                mapnode_to = 0
                if(to_node > 0):
                    # print(to_node)
                    mapnode_to = demand.get_map_node(to_node)
                _total_time[from_node][to_node] = int(
                    travel_minutes_matrix.loc[mapnode_from,mapnode_to]
                    + service_time
                    # adding service time at both ends would double count
                    # + demand.service_time(to_node)
                )

    def time_callback(manager, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # calling pandas object might break C++, so switched to
        return _total_time[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return time_callback

def create_dist_callback(dist_matrix,
                         demand):
    """ create a callback function for dist """

    # preprocess travel and service dist to speed up solver
    _total_dist = {}
    depot_list = np.array([0]) # hack---will fail when depots is not just node 0
    node_list = np.append(depot_list,demand.get_node_list())
    for from_node in node_list:
        _total_dist[from_node] = {}
        mapnode_from = 0
        if (from_node>0):
            mapnode_from = demand.get_map_node(from_node)
        for to_node in node_list:
            if from_node == to_node:
                _total_dist[from_node][to_node] = 0
            else:
                mapnode_to = 0
                if(to_node > 0):
                    # print(to_node)
                    mapnode_to = demand.get_map_node(to_node)
                _total_dist[from_node][to_node] = int(
                    dist_matrix.loc[mapnode_from,mapnode_to]
                )

    def dist_callback(manager, from_index, to_index):
        """Returns the travel dist between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # calling pandas object might break C++, so switched to
        return _total_dist[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return dist_callback
