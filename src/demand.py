import pandas as pd
import numpy as np
import read_csv as reader
import breaks
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
                 dropoff_time=15):

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
            # depot to origin
            do_tt = time_matrix.loc[0,record.from_node]
            # 11 hr drive rule
            do_breaks = math.floor(do_tt/60/11)
            # origin to destination
            od_tt = time_matrix.loc[record.from_node,record.to_node]
            # 11 hr drive rule
            od_breaks = math.floor(od_tt/60/11)
            # destination to depot
            dd_tt = time_matrix.loc[record.to_node,0]
            # 11 hr drive rule
            dd_breaks = math.floor(dd_tt/60/11)

            depot_origin_tt = do_tt + do_breaks*600
            round_trip = (record.pickup_time +
                          od_tt + od_breaks*600 +
                          record.dropoff_time +
                          dd_tt + dd_breaks*600 )
            if record.early > depot_origin_tt:
                round_trip += record.early
            else:
                # don't use early time.  earliest arrival possible is depot_origin_tt
                round_trip += depot_origin_tt

            if round_trip > horizon:
                print("Pair from {} to {} will end at {}, after horizon time of {}".format(record.from_node,record.to_node,round_trip,horizon))
                feasible = False
            if depot_origin_tt > record.late:
                print("Pair from {} to {} has infeasible pickup time.  {} is less than earliest arrival possible of {}".format(record.from_node,record.to_node,
                                                                                                                               record.late,depot_origin_tt))
                feasible = False
            return pd.Series([math.ceil(round_trip),math.ceil(do_tt + do_breaks*600),feasible],index=['round_trip','depot_origin','feasible'])

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
        origins = origins.rename(index=str,columns={'from_node':'mapnode',
                                                    'origin':'modelnode',
                                                    'pickup_time':'service_time'})
        origins.set_index('modelnode',inplace=True)
        origins['demand'] = 1
        self.origins = origins # for queries---is this origin or not

        destinations = self.demand.loc[feasible_index,['to_node','destination','dropoff_time']]
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

    def get_first_break(self,num_veh,time_matrix):

        # function
        def trip_breaks(record):
            """Use travel time matrix to compute timings for breaks.  Assumes the
               passed in record will be the first trip from the depot
               for the vehicle

            """
            # depot to origin drive time
            do_tt = time_matrix.loc[0,record.origin]
            # 11 hr drive rule
            do_breaks = math.floor(do_tt/60/11)
            #do_total_time = do_tt + (do_breaks * 10 * 60)
            do_total_time = do_tt + do_breaks*600

            # origin to destination drive time
            od_tt = time_matrix.loc[record.origin,record.destination]
            # 11 hr drive rule
            od_breaks = math.floor(od_tt/60/11)
            od_total_time = od_tt + od_breaks*600
            # to satisfy this trip, vehicle must execute all required
            # breaks
            min_starting_time = record.early - do_total_time
            if record.early < do_total_time:
                assert record.late >= do_total_time
                min_starting_time = 0
            # print (record)
            # print(do_tt,do_breaks,do_total_time)
            # print(od_tt,od_breaks,od_total_time)
            # print(min_starting_time)
            if min_starting_time < 0:
                # hmm, that is a problem.  explore why this happens
                print (record)
                print(do_tt,do_breaks,do_total_time)
                print(od_tt,od_breaks,od_total_time)
                print(min_starting_time)
                assert 0
            time_window = record.late - record.early
            break_times=[(
                math.floor(min_starting_time + (11*60*(i+1)) + (10*60*i)),
                math.floor(min_starting_time + (11*60*(i+1)) + (10*60*i) + time_window),
                record.origin,int(do_total_time)
            ) for i in range(0,do_breaks)]

            min_depart_time = record.early + record.pickup_time

            break_times.extend([(
                math.floor(min_depart_time + (11*60*(i+1)) + (10*60*i)),
                math.floor(min_depart_time + (11*60*(i+1)) + (10*60*i) + time_window),
                record.destination,int(od_total_time)
            ) for i in range(0,od_breaks)])
            # print (break_times)
            return break_times

        breaks = {}
        feasible_idx = self.demand.feasible
        for idx in self.demand.index[feasible_idx]:
            record = self.demand.loc[idx]
            breaks[record.origin] = trip_breaks(record)

        return breaks

    def get_nth_break(self,num_veh,
                      time_matrix,
                      manager,
                      routing,
                      time_dimension,
                      count_dimension):

        # function
        def trip_breaks(record,veh,routing):
            """Use travel time matrix to compute timings for breaks.  Does not
               assume the passed in record will be the first trip.
               Does assume breaks are taken every 11 hours of driving

            """
            # is a break even relevant?
            od_tt = time_matrix.loc[record.origin,record.destination]
            if record.late + od_tt < 660:
                # do not need a break
                print('do not need a break when serving',record.origin)
                print(record)
                return None

            breaks = []
            # origin to destination drive time
            o_idx = manager.NodeToIndex(record.origin)
            d_idx = manager.NodeToIndex(record.destination)
            # last break end is arrive time - (arrive time mod 11)
            # so next break is that plus 11
            # first break time of drive to destination
            first_break = time_dimension.CumulVar(o_idx)-(time_dimension.CumulVar(o_idx)%11)
            active_node = routing.ActiveVar(o_idx)
            same_vehicle_condition = active_node * routing.VehicleVar(o_idx) == veh
            # break_relevant_condition

            first_10hr_break = solver.FixedDurationIntervalVar(
                # time_start, # minimum start time
                first_break,  # maximum start time (11 hours after start)
                10 * 60,     # duration of break is 10 hours
                same_vehicle_condition,
                'first 10hr break for vehicle {} serving {}'.format(veh,record.origin))
            print(first_10hr_break)
            breaks.append(first_10hr_break)

            # calculate additional breaks

            # 11 hr drive rule
            od_breaks = math.floor(od_tt/60/11)
            od_total_time = od_tt + od_breaks*600

            # to satisfy this trip, vehicle must execute all required
            # breaks
            for intvl in range(1,od_breaks):
                min_start_time = intvl*(10+11)*60
                next_10hr_break = solver.FixedDurationStartSyncedOnStartIntervalVar(
                    first_10hr_break,  # keyed to first
                    600,               # duration
                    min_start_time     # offset
                )
                breaks.append(next_10hr_break)
                # conditions on these seem to have no effect
                # the breaks execute or do not based on first break
            return breaks




        feasible_idx = self.demand.feasible
        for idx in self.demand.index[feasible_idx]:
            record = self.demand.loc[idx]
            breaks[record.origin] = trip_breaks(record)

        return breaks

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
        #   if the link is longer than the timelength, split it in half
        #
        # ditto for each dropoff node and pickup node pairing
        # and for each dropoff node and depot node pairing
        new_node = len(travel_times.index)
        gb = breaks.split_generator(travel_times,timelength)
        # apply to demand pairs
        feasible_index = self.demand.feasible
        newtimes = self.demand.loc[feasible_index,:].apply(gb,axis=1,result_type='reduce')
        # print(newtimes)

        # fixup newtimes into augmented_matrix
        # travel_times = breaks.aggregate_split_nodes(travel_times,newtimes)
        print('First pass, merge',len(newtimes.index),'new times with existing times.')
        travel_times = breaks.aggregate_split_nodes(travel_times,newtimes)
        # print(travel_times)

        print('Next deal with destinations crossed with all origins')

        # now do that for all destinations to all origins plus depot
        # (0). Yes, this can blow up quite large so only merge those that
        # are possible inside horizon given the total travel time


        new_node = len(travel_times.index)
        destination_details = []
        origin_details = []
        for idx in self.demand.index[feasible_index]:
            record = self.demand.loc[idx]
            do_tt = travel_times.loc[0,record.origin]
            do_breaks = (math.floor(do_tt/60/11)) * 60*10
            do_total = do_tt + do_breaks
            origin_trip_cost = record['round_trip'] - do_total

            od_tt = travel_times.loc[record.origin,record.destination]
            od_breaks = (math.floor(do_tt/60/11)) * 60*10
            od_total = od_tt + od_breaks

            dd_tt = travel_times.loc[record.destination,0]
            dd_breaks = (math.floor(dd_tt/60/11)) * 60*10
            dd_total = dd_tt + dd_breaks
            destination_trip_cost = record['round_trip'] - dd_total

            destination_details.append((record.destination,destination_trip_cost,record.origin,record.late+od_total))
            origin_details.append((record.origin,origin_trip_cost,record.destination,record.late))

        for didx in range(0,len(destination_details)):
            dd = destination_details[didx]
            moretimes = []
            for oo in origin_details:
                if dd[1] + oo[1] > self.horizon:
                    continue
                if dd[2] == oo[0]:
                    # that means traveling back to origin, which is impossible
                    continue
                # check that even possible
                tt = travel_times.loc[dd[0],oo[0]]
                if dd[3] + tt > oo[3]:
                    continue
                # trip chain is possible, so split (maybe) destination to origin
                if (not np.isnan(tt)) and  tt > timelength: # don't bother if no break node will happen
                    new_times = breaks.split_links(dd[0],oo[0],tt,new_node)
                    moretimes.append([new_times])
                    new_node += 1
            print(didx,'of',len(destination_details)-1,',append',len(moretimes),'more')
            travel_times = breaks.aggregate_split_nodes(travel_times,moretimes)

        return travel_times # which holds everything of interest
