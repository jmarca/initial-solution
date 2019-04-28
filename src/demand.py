import pandas as pd
import numpy as np
import read_csv as reader

class Demand():
    """
    A class to handle demand.

    Primary job is to convert demand at a map node id, into a demand node
    Every OD pair must map to a unique node, because no nodes can be
    visited twice The "map" nodes in the distance matrix and the demand
    list cannot be used directly.  This class does the conversions.

    """

    def __init__(self,
                 filename,
                 horizon,
                 pickup_time=15,
                 dropoff_time=15):

        demand = reader.load_demand_from_csv(filename)
        # create unique nodes for origins, destinations
        demand['origin'] = range(1,len(demand.index)+1)
        demand['destination'] = demand['origin'].add(len(demand.index))

        # for now, just use identical pickup and dropoff times
        demand['pickup_time']=pickup_time
        demand['dropoff_time']=dropoff_time

        self.demand = demand

        # slice up to create a lookup object
        origins = self.demand.loc[:,['from_node','origin','pickup_time']]
        origins = origins.rename(index=str,columns={'from_node':'mapnode',
                                                    'origin':'modelnode',
                                                    'pickup_time':'service_time'})
        origins.set_index('modelnode',inplace=True)
        origins['demand'] = 1
        self.origins = origins # for queries---is this origin or not

        destinations = self.demand.loc[:,['to_node','destination','dropoff_time']]
        destinations = destinations.rename(index=str,columns={'to_node':'mapnode',
                                                              'destination':'modelnode',
                                                              'dropoff_time':'service_time'})
        destinations.set_index('modelnode',inplace=True)
        destinations['demand'] = -1
        self.destinations = destinations # ditto

        # can look up a map node given a model node
        self.equivalence = origins.append(destinations)

    def get_node_list(self):
        return self.equivalence.index.view(int)

    def get_number_nodes(self):
        return (len(self.equivalence))

    def get_map_node(self,demand_node):
        if demand_node == 0:
            return 0
        return (self.equivalence.loc[demand_node].mapnode)

    def get_service_time(self,demand_node):
        return (self.equivalence.loc[demand_node].service_time)

    def get_demand(self,demand_node):
        d = 0
        if demand_node in self.equivalence:
            d = int(self.equivalence.loc[demand_node,'demand'])
        return d

    def get_demand_map(self):
        _demand = {}
        for idx in self.equivalence.index:
            # from node has 1 supply, to node has -1 demand
            _demand[idx]=self.equivalence.loc[idx,'demand']
        return _demand