# create simple 2D array for distance lookup?
# Define cost of each arc.
import numpy as np
import sys

def create_demand_callback(demand):
    """ create a callback function for demand """
    _demand = demand.get_demand_map()

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
    """create a callback function for time.  presumes that
       travel_minutes_matrix is in solver space, not map space (has
       been passed through demand.generate_solver_space_matrix

    """
    # time matrix is now in model space, not map space
    # preprocess travel and service time to speed up solver
    _total_time = {}

    # nodes are in travel time matrix
    node_list = [n for n in travel_minutes_matrix.index]
    # print('len node list is ',len(node_list))
    for from_node in node_list:
        _total_time[from_node] = {}
        # mapnode_from = demand.get_map_node(from_node)
        service_time = demand.get_service_time(from_node)
        for to_node in node_list:
            if from_node == to_node:
                _total_time[from_node][to_node] = 0
            else:
                # mapnode_to = demand.get_map_node(to_node)
                if not np.isnan(travel_minutes_matrix.loc[from_node,to_node]) :
                    _total_time[from_node][to_node] = int(
                        travel_minutes_matrix.loc[from_node,to_node]
                        + service_time
                    )
                else:
                    _total_time[from_node][to_node] = sys.maxsize
                # print(from_node,to_node,mapnode_from,mapnode_to,_total_time[from_node][to_node])

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
    # dist matrix is now in model space, not map space
    # preprocess travel and service dist to speed up solver
    _total_dist = {}
    # can get node list from dist matrix now
    node_list = [ n for n in dist_matrix.index ]
    for from_node in node_list:
        _total_dist[from_node] = {}
        # no longer need to get map node, as distance matrix is in solver node space
        # mapnode_from = demand.get_map_node(from_node)

        for to_node in node_list:
            if from_node == to_node:
                _total_dist[from_node][to_node] = 0
            else:
                # mapnode_to = demand.get_map_node(to_node)
                if not np.isnan(dist_matrix.loc[from_node,to_node]) :
                    _total_dist[from_node][to_node] = int(
                        dist_matrix.loc[from_node,to_node]
                    )
                else:
                    _total_dist[from_node][to_node] = sys.maxsize


    def dist_callback(manager, from_index, to_index):
        """Returns the travel dist between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # calling pandas object might break C++, so switched to
        return _total_dist[from_node][to_node]

    # return the callback, which will need to be set up with partial
    return dist_callback
