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
                 horizon):
        demand = reader.load_demand_from_csv(filename)
        assert (demand.early.min() > 0)
        assert (demand.early.max() < horizon)
        assert (demand.late.min() > 0)
        assert (demand.late.max() < horizon)

        # create unique nodes for origins, destinations
        demand['origin'] = range(len(demand.index))
        demand['destination'] = demand['origin'].add(len(demand.index))
        self.demand = demand

        # slice up to create a lookup object
        origins = self.demand.loc[:,['from_node','origin']]
        origins = origins.rename(index=str,columns={'from_node':'mapnode',
                                          'origin':'modelnode'})
        origins.set_index('modelnode',inplace=True)
        destinations = self.demand.loc[:,['to_node','destination']]
        destinations = destinations.rename(index=str,columns={'to_node':'mapnode',
                                          'destination':'modelnode'})
        destinations.set_index('modelnode',inplace=True)

        # can look up a map node given a model node
        self.equivalence = origins.append(destinations)
        assert (len(self.equivalence) == len(origins) + len(destinations))

    def get_number_nodes(self):
        return (demand.destination.max() + 1)

    def get_map_node(self,demand_node):
        return (self.equivalence.iat[demand_node].mapnode)
