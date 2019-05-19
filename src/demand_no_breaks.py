import pandas as pd
import numpy as np
import itertools
import read_csv as reader
import sys
import math

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
                 time_matrix,
                 horizon,
                 pickup_time=15,
                 dropoff_time=15,
                 debug = False):

        self.debug = debug
        demand = reader.load_demand_from_csv(filename)
        # for now, just use identical pickup and dropoff times
        demand['pickup_time']=pickup_time
        demand['dropoff_time']=dropoff_time
        self.horizon = horizon
        # check feasible demands based on time_matrix, horizon
        def check_feasible(record):
            """Use travel time matrix to check that every trip is at least
            feasible as a one-off, that is, as a trip from depot to pickup
            to destination and back to depot, respecting both the horizon
            time of the simulation, and the time window of the pickup.

            Infeasible nodes will be marked as such here, so that they
            will not be used in the simulation.

            """
            feasible = True
            constraint = "None"
            # depot to origin
            do_tt = time_matrix.loc[0,record.from_node]

            # origin to destination
            od_tt = time_matrix.loc[record.from_node,record.to_node]

            # destination to depot
            dd_tt = time_matrix.loc[record.to_node,0]

            depot_origin_tt = do_tt + record.pickup_time

            earliest_pickup = record.early
            if record.early < depot_origin_tt:
                earliest_pickup = depot_origin_tt

            time_return_depot = (earliest_pickup + # arrive at orign
                                 record.pickup_time + # load up
                                 od_tt + dd_tt +      # link travel time
                                 record.dropoff_time # unload
            )


            time_destination = (earliest_pickup + # arrive at orign
                                record.pickup_time + # load up
                                dd_tt +      # link travel time
                                record.dropoff_time # unload
            )


            if time_return_depot > horizon:
                constraint = "Pair from {} to {} will end at {}, after horizon time of {}".format(record.from_node,record.to_node,time_return_depot,horizon)
                print(constraint)
                feasible = False
            if depot_origin_tt > record.late:
                constraint = "Pair from {} to {} has infeasible pickup time.  {} is less than earliest arrival possible of {}".format(record.from_node,record.to_node,
                                                                                                                               record.late,depot_origin_tt)
                print(constraint)
                feasible = False
            return pd.Series([math.ceil(time_return_depot),
                              math.ceil(depot_origin_tt),
                              math.ceil(time_destination),
                              feasible,
                              constraint],
                             index=['round_trip',
                                    'depot_origin',
                                    'earliest_destination',
                                    'feasible',
                                    'constraint'])

        morecols = demand.apply(check_feasible,axis=1)
        # print(morecols)
        demand = demand.join(morecols)
        # print(demand)
        demand['origin'] = -1
        demand['destination'] = -1
        feasible_index = demand.feasible
        # print(feasible_index)
        # create unique nodes for origins, destinations
        demand.loc[feasible_index,'origin'] = range(1,len(demand.index[feasible_index])+1)
        last_origin = demand.origin.max()
        demand.loc[feasible_index,'destination'] = last_origin + range(1,len(demand.index[feasible_index])+1)
        # so now, feasible pairs have origin, destination > 0
        # and infeasible pairs have origin = -1, destination = -1
        self.demand = demand

        # slice up to create a lookup object
        origins = self.demand.loc[feasible_index,['from_node','origin','pickup_time']]
        origins['demand_index'] = origins.index
        origins = origins.rename(index=str,columns={'from_node':'mapnode',
                                                    'origin':'modelnode',
                                                    'pickup_time':'service_time'})
        origins.set_index('modelnode',inplace=True)
        origins['demand'] = 1

        self.origins = origins # for queries---is this origin or not

        destinations = self.demand.loc[feasible_index,['to_node','destination','dropoff_time']]
        destinations['demand_index'] = destinations.index
        destinations = destinations.rename(index=str,columns={'to_node':'mapnode',
                                                              'destination':'modelnode',
                                                              'dropoff_time':'service_time'})
        destinations.set_index('modelnode',inplace=True)
        destinations['demand'] = -1
        self.destinations = destinations # ditto
        # can look up a map node given a model node
        self.equivalence = origins.append(destinations)
        self.break_nodes = None

    def get_break_node(self,i):
        return None

    def get_node_list(self):
        return self.equivalence.index.view(int)

    def get_map_node(self,demand_node):
        if demand_node == 0:
            return 0
        if demand_node in self.equivalence.index:
            return (self.equivalence.loc[demand_node].mapnode)
        # handles case of depot, and all augmenting nodes for
        # breaks, etc
        return -1

    def get_demand_number(self,demand_node):
        if demand_node in self.equivalence.index:
            return (self.equivalence.loc[demand_node].demand_index)
        return -1

    def get_service_time(self,demand_node):
        if demand_node in self.equivalence.index:
            return (self.equivalence.loc[demand_node].service_time)
        return 0

    def get_time_window(self,demand_node):
        if demand_node in self.origins.index:
            # find it in the original demand list
            record_idx = self.demand.origin == demand_node
            time_windows = self.demand.loc[record_idx,['early','late']].iloc[0,:].view('int')
            return (time_windows[0],time_windows[1])
        return (0,self.horizon)

    def get_min_intervals(self,num_veh):
        min_intervals = [0 for i in range(0,num_veh)]
        # sift through sorted early values.  as early increments, increment min_intervals
        sorted_early = self.demand.early.view('int').sort_values()
        min_early = sorted_early.iloc[0]
        offset = 0
        for i in range(1,num_veh):
            if sorted_early.iloc[i] > min_early:
                min_early = sorted_early.iloc[i]
                offset += 1
            min_intervals[i] += offset
        return min_intervals


    def get_node_visit_transit(self,time_matrix):
        node_visit_transit = {}
        for n in time_matrix.index:
            node_visit_transit[n] = int(self.get_service_time(n))
        return node_visit_transit


    def get_starting_times(self):
        """get a list of starting time windows, and the longest time to depot,
        in order to approximate likely time windows for vehicle
        starts

        """
        result = self.demand.loc[:,['depot_origin','early']].groupby(['early'],as_index=False)
        return (result.count().get_values(),result.max().get_values())


    def get_demand(self,demand_node):
        if demand_node in self.equivalence.index:
            return int(self.equivalence.loc[demand_node,'demand'])
        return 0

    def generate_solver_space_matrix(self,matrix,horizon=None):
        """the input distance matrix is in "map space", meaning that nodes can
        repeat and so on.  The solver cannot work in that space, so
        this routine converts.  Input is a matrix of distances between
        nodes, output is the same data, but reindexed and possibly
        repeated for nodes in solver space.

        """
        if(horizon == None):
            horizon=self.horizon
        # iterate over each entry in the matrix, and make a new matrix
        # with same data.
        new_matrix = {}
        new_matrix[0] = {} # depot node
        new_matrix[0][0] = 0
        # list of all origins
        self.demand['load_number'] = self.demand.index
        feasible_idx = self.demand.feasible
        for idx in self.demand.index[feasible_idx]:
            record = self.demand.loc[idx]
            if not record.origin in new_matrix.keys():
                new_matrix[record.origin]={}
                new_matrix[record.origin][record.origin] = 0
            if not record.destination in new_matrix.keys():
                new_matrix[record.destination]={}
                new_matrix[record.destination][record.destination]=0
            # depot to origin
            new_matrix[0][record.origin]=matrix.loc[0,record.from_node]
            # origin to destination
            new_matrix[record.origin][record.destination]=matrix.loc[record.from_node,
                                                                     record.to_node]
            # destination to self
            new_matrix[record.destination][record.destination]=0
            # destination to depot
            new_matrix[record.destination][0]=matrix.loc[record.to_node,0]


        # finally, link all feasible destinations to all feasible origins
        for d in self.destinations.index:
            for o in self.origins.index:
                if d in new_matrix[o].keys():
                    # this is original o to d pair, don't link d to o
                    continue
                new_matrix[d][o]=matrix.loc[self.get_map_node(d),
                                            self.get_map_node(o)]
        df = pd.DataFrame.from_dict(new_matrix,orient='index')
        # df = df.fillna(sys.maxsize)
        # I like this prior to solver run, but here is it potentially dangerous
        return df
