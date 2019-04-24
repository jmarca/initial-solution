# create simple 2D array for distance lookup?
# Define cost of each arc.

def create_time_callback(travel_minutes_matrix,
                         demand):
    """ create a callback function for time """

    # preprocess travel and service time to speed up solver
    _total_time = {}
    for from_node in range(0, demand.get_number_nodes()):
        _total_time[from_node] = {}
        mapnode_from = demand.get_map_node(from_node)
        for to_node in range(0, demand.get_number_nodes()):
            if from_node == to_node:
                _total_time[from_node][to_node] = 0
            else:
                mapnode_to = demand.get_map_node(to_node)
                _total_time[from_node][to_node] = int(
                    travel_minutes_matrix.iloc[mapnode_from,mapnode_to]
                    + demand.get_service_time(from_node)
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


# not really necessary with truck load problem, as one pickup fills the truck
# def create_demand_callback(demand):
#     """ create a demand callback function
#     At this point, it is just 1, -1 everywhere
#     """
#     # try sticking with pandas, see if it crashes C++

#     def demand_callback(manager, from_index, to_index):
#         """Returns the demand (1 for pickup, or -1 for dropoff) at node"""
#         # Convert from routing variable Index to distance matrix NodeIndex.
#         from_node = manager.IndexToNode(from_index)
#         to_node = manager.IndexToNode(to_index)
#         # calling pandas object might break C++, so switched to
#         return _total_time[from_node][to_node]

#     # return the callback, which will need to be set up with partial
#     return time_callback
