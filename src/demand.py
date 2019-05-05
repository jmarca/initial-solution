import pandas as pd
import numpy as np
import read_csv as reader
import breaks
import sys

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
                 dropoff_time=15):

        demand = reader.load_demand_from_csv(filename)
        # for now, just use identical pickup and dropoff times
        demand['pickup_time']=pickup_time
        demand['dropoff_time']=dropoff_time

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
            round_trip = (time_matrix.loc[0,record.from_node] +
                          record.pickup_time +
                          time_matrix.loc[record.from_node,record.to_node] +
                          record.dropoff_time +
                          time_matrix.loc[record.to_node,0] +
                          record.early)
            if round_trip > horizon:
                print("Pair from {} to {} will end after horizon time of {}".format(record.from_node,record.to_node,horizon))
                feasible = False
            return feasible
        demand['feasible'] = demand.apply(check_feasible,axis=1)


        # create unique nodes for origins, destinations
        demand['origin'] = range(1,len(demand.index)+1)
        demand['destination'] = demand['origin'].add(len(demand.index))

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

    def get_map_node(self,demand_node):
        if demand_node in self.equivalence.index:
            return (self.equivalence.loc[demand_node].mapnode)
        # handles case of depot, and all augmenting nodes for
        # breaks, etc
        return demand_node

    def get_service_time(self,demand_node):
        if demand_node in self.equivalence.index:
            return (self.equivalence.loc[demand_node].service_time)
        return 0

    def get_demand(self,demand_node):
        if demand_node in self.equivalence.index:
            return int(self.equivalence.loc[demand_node,'demand'])
        return 0

    def get_demand_map(self):
        _demand = {}
        for idx in self.equivalence.index:
            # from node has 1 supply, to node has -1 demand
            _demand[idx]=self.equivalence.loc[idx,'demand']
        return _demand

    def generate_solver_space_matrix(self,matrix,horizon):
        """the input distance matrix is in "map space", meaning that nodes can
        repeat and so on.  The solver cannot work in that space, so
        this routine converts.  Input is a matrix of distances between
        nodes, output is the same data, but reindexed and possibly
        repeated for nodes in solver space.

        """
        # iterate over each entry in the matrix, and make a new matrix
        # with same data.
        new_matrix = {}
        new_matrix[0] = {} # depot node
        new_matrix[0][0] = 0
        # list of all origins
        self.demand['feasible'] = True
        feasible_origins = []
        feasible_destinations = []
        for idx in self.demand.index:
            record = self.demand.loc[idx]
            """Use travel time matrix to check that every trip is at least
            feasible as a one-off, that is, as a trip from depot to pickup
            to destination and back to depot, respecting both the horizon
            time of the simulation, and the time window of the pickup.

            Infeasible nodes will be marked as such here, so that they
            will not be used in the simulation.

            """
            round_trip = (matrix.loc[0,record.from_node] + record.pickup_time +
                          matrix.loc[record.origin,record.to_node] + record.dropoff_time +
                          matrix.loc[record.to_node,0] + record.early)
            if round_trip > horizon:
                print("Pair from {} to {} will end after horizon time of {}".format(record.from_node,record.to_node,horizon))
                self.demand.loc[idx,'feasible']=False
                continue
            feasible_origins.append(record.origin)
            feasible_destinations.append(record.destination)
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
        for d in feasible_destinations:
            for o in feasible_origins:
                if d in new_matrix[o].keys():
                    # this is original o to d pair, don't link d to o
                    continue
                new_matrix[d][o]=matrix.loc[self.get_map_node(d),
                                            self.get_map_node(o)]
        df = pd.DataFrame.from_dict(new_matrix,orient='index')
        # df = df.fillna(sys.maxsize)
        # I like this prior to solver run, but here is it potentially dangerous
        return df



    def make_break_nodes(self,travel_times,timelength=600):
        """Use travel time matrix, pickup and dropoff pairs to create the
        necessary break opportunities between pairs of nodes.  Assumes
        that travel_times are in solver space, that is, the original
        "map space" travel times have been run through a call to
        generate_solver_space_matrix already.  Will default to 10 hours per break

        """

        # logic:
        #
        # for each pickup and dropoff pair in the demand records,
        #
        #   create a potential break node every hour along the route.
        #
        # ditto for each dropoff node and pickup node pairing
        # and for each dropoff node and depot node pairing
        new_node = len(travel_times[0])
        gb = breaks.break_generator(travel_times,timelength)
        # apply to demand pairs
        newtimes = self.demand.apply(gb,axis=1,result_type='reduce')

        # fixup newtimes into augmented_matrix
        travel_times = breaks.aggregate_time_matrix(travel_times,newtimes)

        # now do that for all destinations to all origins plus depot (0)
        # yes, this blows up quite large
        moretimes = []

        destinations_idx = [idx for idx in self.destinations.index]
        destinations_idx.append(0) # tack on the depot node
        origins_idx = [idx for idx in self.origins.index]
        origins_idx.append(0) # tack on the depot node.  This will
                              # fail if/when more than one depot
                              # happens
        # print(max(travel_times.columns))

        # now assuming that travel matrix is in solver space. no need
        # for mapnode stuff
        for didx in destinations_idx:
            # d_mapnode = self.get_map_node(didx)
            for oidx in origins_idx:
                if oidx == didx:
                    # depot to depot is silly
                    continue
                # o_mapnode = self.get_map_node(oidx)
                tt = travel_times.loc[didx,oidx]
                if (not np.isnan(tt)) and  tt > timelength: # don't bother if no break node will happen
                    new_times = breaks.make_nodes(didx,oidx,tt,new_node,timelength)
                    moretimes.append(new_times)

        travel_times = breaks.aggregate_time_matrix(travel_times,moretimes)
        return travel_times # which holds everything of interest
