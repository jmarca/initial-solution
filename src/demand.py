import pandas as pd
import numpy as np
import breaks
import break_node as BN
import math
from functools import partial

def zeroed_trip_triplets(num):
    return np.zeros(num,dtype=[('x', int), ('y', int),('t',float)])



class Demand():
    """
    A class to handle demand.

    Primary job is to convert demand at a map node id, into a demand node
    Every OD pair must map to a unique node, because no nodes can be
    visited twice The "map" nodes in the distance matrix and the demand
    list cannot be used directly.  This class does the conversions.

    """

    def estimate_break_time(self,tt,long_break,short_break):
        # long breaks, calc number of breaks
        long_break_time = long_break.break_time
        long_break_period = long_break.accumulator_reset
        short_break_time = short_break.break_time
        short_break_period = short_break.accumulator_reset

        num_long_breaks = math.floor(tt / long_break_period)


        # for each long break, will also need at least one short break
        # but *might* need another if drive time works out that way
        # drive time is do_tt
        # every 11 hr, 8 hr clock resets to zero
        num_short_breaks = num_long_breaks
        if tt - (num_long_breaks*long_break_period) > short_break_period:
            num_short_breaks += 1

        # sum the two
        return num_long_breaks*long_break_time + num_short_breaks*short_break_time

    def check_feasible(self, time_matrix, long_break, short_break, record):
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
        do_tt = time_matrix.loc[0, record.from_node]

        # origin to destination
        od_tt = time_matrix.loc[record.from_node, record.to_node]

        # destination to depot
        dd_tt = time_matrix.loc[record.to_node, 0]

        do_break_time = 0
        od_dd_break_time = 0
        od_break_time = 0
        if long_break:
            do_break_time = self.estimate_break_time(do_tt,long_break,short_break)
            od_dd_break_time = self.estimate_break_time(od_tt+dd_tt,long_break,short_break)
            od_break_time = self.estimate_break_time(od_tt,long_break,short_break)


        depot_origin_tt = do_tt + record.pickup_time+do_break_time

        earliest_pickup = record.early
        if record.early < depot_origin_tt:
            earliest_pickup = depot_origin_tt

        time_return_depot = (earliest_pickup +     # arrive at orign
                             record.pickup_time +  # load up
                             record.dropoff_time +  # unload
                             od_tt +               # travel time to dest
                             dd_tt +               # travel time to depot
                             od_dd_break_time      # breaks?
        )

        time_destination = (earliest_pickup +
                            record.pickup_time +
                            od_tt +
                            od_break_time)

        if time_return_depot > self.horizon:
            constraint = "Pair from {} to {} will end at {}, after horizon time of {}".format(record.from_node,record.to_node,time_return_depot,self.horizon)
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

    def __init__(self,
                 odpairs,
                 time_matrix,
                 horizon,
                 pickup_time=15,
                 dropoff_time=15,
                 debug=False,
                 use_breaks=True):

        self.debug = debug
        self.horizon = horizon
        demand = odpairs.copy()
        # for now, just use identical pickup and dropoff times
        demand['pickup_time']=pickup_time
        demand['dropoff_time']=dropoff_time
        # check feasible demands based on time_matrix, horizon
        long_break = None
        short_break = None
        if use_breaks:
            long_break  = BN.BreakNode(-1, -1, 660, 0, 600, 660)
            short_break = BN.BreakNode(-1, -1, 480, 0,  30, 480)

        morecols = demand.apply(partial(self.check_feasible,
                                        time_matrix,
                                        long_break, short_break), axis=1)

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
        self.break_node_chains = None

    def get_node_list(self):
        return self.equivalence.index.view(int)

    def _get_demand_entry(self,demand_node,entry,default):
        if demand_node in self.equivalence.index:
            return int(self.equivalence.loc[demand_node,entry])
        return default

    def get_map_node(self,demand_node):
        if demand_node == 0:
            return 0
        return self._get_demand_entry(demand_node,'mapnode',-1)

    def get_demand_number(self,demand_node):
        return self._get_demand_entry(demand_node,'demand_index',-1)

    def get_service_time(self,demand_node):
        return self._get_demand_entry(demand_node,'service_time',0)

    def get_demand(self,demand_node):
        return self._get_demand_entry(demand_node,'demand',0)

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
        new_times = zeroed_trip_triplets(1)
        new_matrix = {}

        # list of all origins
        self.demand['load_number'] = self.demand.index
        feasible_idx = self.demand.feasible
        def travtime(record):
            record_times = zeroed_trip_triplets(5)
            record_times[0]=(record.origin, record.origin,0.0)
            record_times[1]=(record.destination, record.destination,0.0)
            record_times[2]=(record.origin, record.destination,
                             matrix.loc[record.from_node, record.to_node])
            record_times[3]=(0,record.origin,
                             matrix.loc[0, record.from_node])
            record_times[4]=(record.destination,0,
                             matrix.loc[record.to_node, 0])
            return record_times


        for idx in self.demand.index[feasible_idx]:
            record = self.demand.loc[idx]
            new_times = np.append(new_times,travtime(record),axis=0)
            other_feasible = feasible_idx.copy()
            other_feasible[idx] = False
            if len(other_feasible[other_feasible])>0:
                # link destination to all other feasible origins
                other_times = [(record.destination, onode, matrix.loc[record.to_node,omap])
                               for (onode,omap) in self.demand.loc[other_feasible,
                                                         ['origin','from_node']].values]

                triple = np.array(other_times,
                                  dtype=[('x', int), ('y', int),('t',float)])
                new_times = np.append(new_times,triple,axis=0)
        df = pd.DataFrame(new_times)
        df.drop_duplicates(inplace=True)
        df = df.pivot(index='x',columns='y',values='t')

        # df = df.fillna(sys.maxsize)
        # I like this prior to solver run, but here is it potentially dangerous
        return df



    def insert_nodes_for_breaks(self,travel_times):
        """Use travel time matrix, pickup and dropoff pairs to create the
        necessary dummy nodes for modeling breaks between pairs of nodes.

        """

        # logic:
        #
        # for each pickup and dropoff pair in the demand records,
        #
        #   split it in half, insert a break
        #
        # ditto for each dropoff node and pickup node pairing
        # and for each dropoff node and depot node pairing
        new_node = len(travel_times.index)
        # gb = breaks.split_break_node_generator(travel_times)
        # apply to demand pairs
        feasible_index = self.demand.feasible
        # can't use apply here...it breaks
        # new_times_nodes = self.demand.loc[feasible_index,:].apply(gb,axis=1,result_type='reduce')
        self.break_nodes = {}
        self.break_node_chains = {}
        self.break_node_chains[0]={}
        new_times = zeroed_trip_triplets(0)
        for idx in self.demand.index[feasible_index]:
            record = self.demand.loc[idx]
            pair = breaks.split_break_node(record,travel_times,new_node)
            # travel_times = breaks.aggregate_split_nodes(travel_times,pair[0])
            new_times = np.concatenate((new_times, pair[0]), axis=0)
            new_node = pair[2]
            for bn in  pair[1]:
                self.break_nodes[bn.node]=bn
                # from 0, origin, or destination
                if bn.destination == record.origin:
                    # this break from depot to origin
                    if not record.origin in self.break_node_chains[0]:
                        self.break_node_chains[0][record.origin]=[]
                    self.break_node_chains[0][record.origin].append(bn.node)
                if bn.destination == record.destination:
                    # this break from origin to destination
                    if not record.origin in self.break_node_chains:
                        self.break_node_chains[record.origin]={}
                    if not record.destination in self.break_node_chains[record.origin]:
                        self.break_node_chains[record.origin][record.destination]=[]
                    self.break_node_chains[record.origin][record.destination].append(bn.node)
                if bn.destination == 0:
                    # this break from destination to depot
                    if not record.destination in self.break_node_chains:
                        self.break_node_chains[record.destination]={}
                    if not 0 in self.break_node_chains[record.destination]:
                        self.break_node_chains[record.destination][0]=[]
                    self.break_node_chains[record.destination][0].append(bn.node)

                # print('checking',bn.origin,bn.node,bn.destination)
                # assert int(travel_times.loc[bn.origin,bn.node]) == bn.tt_o
                # assert int(travel_times.loc[bn.node,bn.destination]) == bn.tt_d
            assert new_node > max(self.break_nodes.keys())

        # fighting memory bloat; incorporate the new travel times
        # travel_times = breaks.aggregate_split_nodes(travel_times,new_times)
        # new_times = []
        # print(self.break_node_chains)

        print('Next deal with destinations crossed with all origins')

        # now do that for all destinations to all origins plus depot
        # (0). Yes, this can blow up quite large so only merge those that
        # are possible inside horizon given the total travel time


        # new_node = len(travel_times.index)
        destination_details = []
        origin_details = []
        for idx in self.demand.index[feasible_index]:
            record = self.demand.loc[idx]
            destination_details.append((record.destination,
                                        record.earliest_destination,
                                        record.origin))
            origin_details.append((record.origin,
                                   record.late))
        for dd in destination_details:
            didx = dd[0]
            # moretimes = []
            for oo in origin_details:
                oidx = oo[0]
                if dd[2] == oidx:
                    # that means traveling back to origin, which is impossible
                    continue
                # what is min time to destination, and from then, can
                # we get to origin before horizon?
                tt = travel_times.loc[didx,oidx]
                assert not np.isnan(tt)
                if dd[1] + tt > self.horizon:
                    if self.debug:
                        print("can't get from",didx,"to",oidx,"before horizon")
                    continue
                # check that can get to next origin before its time horizon ends
                if dd[1] + tt > oo[1]:
                    if self.debug:
                        print("can't get from",didx,"to",oidx,"before origin pickup horizon",oo[1])
                    continue
                # trip chain is possible, so split destination to origin
                pair = breaks.break_node_splitter(dd[0],oo[0],tt,new_node)
                new_times = np.concatenate((new_times, pair[0]), axis=0)
                #print(new_times[-2])
                #print(new_times[-1])

                for nn in pair[1]:
                    if self.debug:
                        print('add new node',nn.node,'bewteen',nn.origin,nn.destination)
                    self.break_nodes[nn.node] = nn
                    if not dd[0] in self.break_node_chains:
                        self.break_node_chains[dd[0]]={}
                    if not dd[1] in self.break_node_chains[dd[0]]:
                        self.break_node_chains[dd[0]][oo[0]]=[]
                    self.break_node_chains[dd[0]][oo[0]].append(bn.node)
                new_node = pair[2]

            # print(new_times)
            # now at end of inner loop, incorporate the new travel times
        travel_times = breaks.aggregate_split_nodes(travel_times,new_times)
        return travel_times # which holds everything of interest except self.break_nodes


    def get_break_node_chain(self,from_node,to_node):
        if from_node in self.break_node_chains:
            if to_node in self.break_node_chains[from_node]:
                return self.break_node_chains[from_node][to_node]
        return None

    def get_break_node(self,node):
        if self.break_nodes and node in self.break_nodes:
            return self.break_nodes[node]
        return None

    def break_constraint(self,
                         origin,destination,
                         manager,
                         routing,
                         drive_dimension,
                         short_break_dimension,
                         drive_dimension_start_value
    ):
        solver = routing.solver()
        o_idx = manager.NodeToIndex(origin)
        d_idx = manager.NodeToIndex(destination)
        print(origin,o_idx,destination,d_idx)
        origin_active =routing.ActiveVar(o_idx)
        dest_active =routing.ActiveVar(d_idx)

        origin_drive = origin_active*drive_dimension.CumulVar(o_idx)
        dest_drive = dest_active*drive_dimension.CumulVar(d_idx)

        origin_short = origin_active*short_break_dimension.CumulVar(o_idx)
        dest_short = dest_active*short_break_dimension.CumulVar(d_idx)

        # print(origin_drive,'>=',origin_active,'*',drive_dimension_start_value)
        solver.AddConstraint(origin_drive >= origin_active*drive_dimension_start_value)

        # print(origin_drive,'<=',origin_active,'*',drive_dimension_start_value+660)
        solver.AddConstraint(origin_drive < origin_active*(drive_dimension_start_value)+660)

        # print(dest_drive,'>=',dest_active,'*',drive_dimension_start_value)
        solver.AddConstraint(dest_drive >= dest_active*drive_dimension_start_value)

        # print(dest_drive,'<=',dest_active,'*',drive_dimension_start_value+660)
        solver.AddConstraint(dest_drive < dest_active*(drive_dimension_start_value)+660)

        # same type of constraints for short drive dimension, except 8 hrs not 11 hrs

        # print(origin_short,'<',origin_active,'*',drive_dimension_start_value+8*60)
        solver.AddConstraint(origin_short < origin_active*(drive_dimension_start_value)+(8*60))
        # print(origin_short,'>=',origin_active,'*',drive_dimension_start_value)
        solver.AddConstraint(origin_short >= origin_active*drive_dimension_start_value)

        # print(dest_short,'<',dest_active,'*',drive_dimension_start_value+8*60)
        solver.AddConstraint(dest_short < dest_active*(drive_dimension_start_value)+(8*60))

        # print(dest_short,'>=',dest_active,'*',drive_dimension_start_value)
        solver.AddConstraint(dest_short >= dest_active*drive_dimension_start_value)
