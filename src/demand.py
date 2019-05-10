import pandas as pd
import numpy as np
import itertools
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

            # depot to origin
            do_tt = time_matrix.loc[0,record.from_node]

            # origin to destination
            od_tt = time_matrix.loc[record.from_node,record.to_node]

            # destination to depot
            dd_tt = time_matrix.loc[record.to_node,0]

            # 11 hr drive rule, calc number of breaks
            total_breaks = math.floor( (do_tt+od_tt+dd_tt) / (60*11) )
            cumul_break_time = total_breaks * 600

            do_breaks = math.floor(do_tt/(11*60))
            depot_origin_tt = do_tt + do_breaks*600 + record.pickup_time

            pickup_to_depot_breaks = total_breaks - do_breaks

            od_breaks = math.floor((do_tt + od_tt)/(11*60)) - do_breaks

            earliest_pickup = record.early
            if record.early < depot_origin_tt:
                earliest_pickup = depot_origin_tt

            time_return_depot = (earliest_pickup + # arrive at orign
                                 record.pickup_time + # load up
                                 od_tt + dd_tt +      # link travel time
                                 record.dropoff_time +# unload
                                 pickup_to_depot_breaks*600 ) # required 10hr breaks

            time_destination = (earliest_pickup + # arrive at orign
                                record.pickup_time + # load up
                                dd_tt +      # link travel time
                                record.dropoff_time +# unload
                                od_breaks*600 ) # required 10hr breaks from O to D

            if time_return_depot > horizon:
                print("Pair from {} to {} will end at {}, after horizon time of {}".format(record.from_node,record.to_node,time_return_depot,horizon))
                feasible = False
            if depot_origin_tt > record.late:
                print("Pair from {} to {} has infeasible pickup time.  {} is less than earliest arrival possible of {}".format(record.from_node,record.to_node,
                                                                                                                               record.late,depot_origin_tt))
                feasible = False
            return pd.Series([math.ceil(time_return_depot),
                              math.ceil(depot_origin_tt),
                              math.ceil(time_destination),
                              feasible],
                             index=['round_trip',
                                    'depot_origin',
                                    'earliest_destination',
                                    'feasible'])

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
        if demand_node == 0:
            return 0
        if demand_node in self.equivalence.index:
            return (self.equivalence.loc[demand_node].mapnode)
        # handles case of depot, and all augmenting nodes for
        # breaks, etc
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

    def get_node_visit_transit(self,time_matrix):
        node_visit_transit = {}
        for n in time_matrix.index:
            node_visit_transit[n] = int(self.get_service_time(n))
        return node_visit_transit

    def get_simple_breaks(self,num_veh,
                          time_matrix,
                          manager,
                          routing,
                          time_dimension,
                          count_dimension):
        """Clock starts at zero, driving starts at zero, so assume breaks can
           be specified as fixed times between starting of driving
           This version, all breaks are optional, specified individually as ranges

        """

        # function per vehicle
        def trip_breaks(veh,routing):
            solver = routing.solver()
            breaks = []
            # start at 0, 10 hr break every 11 hr of driving

            num_breaks = math.floor(self.horizon/60/(11+10))
            for interval in range(0,num_breaks):
                # break start is after 11 hrs driving + earlier driving+breaks
                start_time = 11*60 + (interval)*(10+11)*60
                # insert the break
                brk = solver.FixedDurationIntervalVar(
                    start_time,  # min start time
                    start_time,  # max start time (same)
                    10*60,  # 10 hour duration
                    False,  # optional
                    # True,  # not optional
                    '10hr break {} for vehicle {}'.format(interval,veh))
                breaks.append(brk)
            return breaks

        breaks = {}
        node_visit_transit = self.get_node_visit_transit(time_matrix)
        for veh in range(0,num_veh):
            breaks[veh] = trip_breaks(veh,routing)
            print(breaks[veh])
            time_dimension.SetBreakIntervalsOfVehicle(
                breaks[veh], veh, node_visit_transit)
        return breaks

    def get_breaks_synced_first(self,num_veh,
                                time_matrix,
                                manager,
                                routing,
                                time_dimension,
                                count_dimension):
        """Clock starts at zero, driving starts at zero, so assume breaks can
           be specified as fixed times between starting of driving

        """

        # function per vehicle
        def trip_breaks(veh,routing):
            solver = routing.solver()
            breaks = []
            # start at 0, 10 hr break every 11 hr of driving

            num_breaks = math.floor(self.horizon/60/(11+10))
            for interval in range(0,num_breaks):
                if len(breaks) == 0:
                    # insert the first break
                    brk = solver.FixedDurationIntervalVar(
                        11*60,  # min start time
                        11*60,  # max start time (same)
                        10*60,  # 10 hour duration
                        False,  # optional
                        # True,  # not optional
                        '10hr break 0 for vehicle {}'.format(veh))
                    breaks.append(brk)
                else:
                    # synced with **start** of first break,
                    # one drive, one break per interval
                    offset = interval*(11+10)*60
                    brk = solver.FixedDurationStartSyncedOnStartIntervalVar(
                        breaks[0], # synced to starting break
                        10*60,     # 10hr duration
                        offset # when to start after first
                    )
                    breaks.append(brk)
            return breaks

        breaks = {}
        node_visit_transit = self.get_node_visit_transit(time_matrix)
        for veh in range(0,num_veh):
            breaks[veh] = trip_breaks(veh,routing)
            print(breaks[veh])
            time_dimension.SetBreakIntervalsOfVehicle(
                breaks[veh], veh, node_visit_transit)
        return breaks

    def get_breaks_synced_first_variable(self,num_veh,
                                         time_matrix,
                                         manager,
                                         routing,
                                         time_dimension,
                                         count_dimension):
        """Clock starts at zero, driving starts at variable time, so breaks
           start at time of vehicle departure, defined as start +
           slack.  All other breaks based on initial break plus 11
           hours

        """

        # function per vehicle
        def trip_breaks(veh,routing):
            solver = routing.solver()
            breaks = []
            # start at 0, 10 hr break every 11 hr of driving
            #
            num_breaks = math.floor(self.horizon/60/(11+10))
            active_start =  routing.ActiveVar(routing.Start(veh))
            active_end = routing.VehicleVar(routing.End(veh)) == veh
            counting_end = active_end * count_dimension.CumulVar(routing.End(veh))
            end_count_okay = counting_end > 1
            active_vehicle = end_count_okay
            time_start = time_dimension.CumulVar(routing.Start(veh))
            slack_start = time_dimension.SlackVar(routing.Start(veh))
            time_end = time_dimension.CumulVar(routing.End(veh))
            must_start = (time_start + slack_start + (11*60)) # 11 hours later
            for interval in range(0,num_breaks):
                if len(breaks) == 0:
                    # insert the first break
                    brk = solver.FixedDurationIntervalVar(
                        must_start,  # min start time
                        10*60,  # 10 hour duration
                        active_vehicle,
                        '10hr break 0 for vehicle {}'.format(veh))
                    breaks.append(brk)
                else:
                    # synced with **start** of first break,
                    # one drive, one break per interval
                    offset = interval*(11+10)*60
                    brk = solver.FixedDurationStartSyncedOnStartIntervalVar(
                        breaks[0], # synced to starting break
                        10*60,     # 10hr duration
                        offset # when to start after first
                    )
                    breaks.append(brk)
            return breaks

        breaks = {}
        node_visit_transit = self.get_node_visit_transit(time_matrix)
        for veh in range(0,num_veh):
            breaks[veh] = trip_breaks(veh,routing)
            print(breaks[veh])
            time_dimension.SetBreakIntervalsOfVehicle(
                breaks[veh], veh, node_visit_transit)
        return breaks

    def get_breaks_unsynced_variable(self,num_veh,
                                     time_matrix,
                                     manager,
                                     routing,
                                     time_dimension,
                                     count_dimension):
        """Clock starts at zero, driving starts at variable time, so breaks
           start at time of vehicle departure, defined as start +
           slack.  All other breaks start if final time is large enough

        """

        # function per vehicle
        def trip_breaks(veh,routing):
            solver = routing.solver()
            breaks = []
            # start at 0, 10 hr break every 11 hr of driving
            #
            num_breaks = math.floor(self.horizon/60/(11+10))
            active_start =  routing.ActiveVar(routing.Start(veh))
            active_end = routing.VehicleVar(routing.End(veh)) == veh
            counting_end = active_end * count_dimension.CumulVar(routing.End(veh))
            end_count_okay = counting_end > 1
            active_vehicle = end_count_okay
            time_start = time_dimension.CumulVar(routing.Start(veh))
            slack_start = time_dimension.SlackVar(routing.Start(veh))
            time_end = time_dimension.CumulVar(routing.End(veh))
            must_start = active_start*(time_start + slack_start + (11*60)) # 11 hours later
            for interval in range(0,num_breaks):
                if interval > 0:
                    must_start = active_start*(time_start +
                                               slack_start +
                                               active_vehicle * (11*60 +  # 11 hours of driving
                                                                 interval*(11+10)*60)) # prior drive/breaks


                #indicator_intvar = active_vehicle
                # indicator_intvar = active_vehicle*(time_start+slack_start)+(11+10)*60 <= active_vehicle*time_end

                indicator_intvar = time_end >=  60 *(11+10)*(interval+1)

                # insert the first break
                brk = solver.FixedDurationIntervalVar(
                    must_start,  # min start time
                    10*60,  # 10 hour duration
                    indicator_intvar,
                    '10hr break 0 for vehicle {}'.format(veh))
                breaks.append(brk)
            return breaks

        breaks = {}
        node_visit_transit = self.get_node_visit_transit(time_matrix)
        for veh in range(0,num_veh):
            breaks[veh] = trip_breaks(veh,routing)
            print(breaks[veh])
            time_dimension.SetBreakIntervalsOfVehicle(
                breaks[veh], veh, node_visit_transit)
        return breaks

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



    def insert_nodes_for_slack(self,travel_times,timelength=600):
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
            # origin_trip_cost = record['round_trip'] - do_total

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


    # FIXME need to expand this likely for the 30 minutes in 8 hours rule
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
        new_times = []
        new_nodes = []
        for idx in self.demand.index[feasible_index]:
            record = self.demand.loc[idx]
            pair = breaks.split_break_node(record,travel_times,new_node)
            travel_times = breaks.aggregate_split_nodes(travel_times,pair[0])
            # print(travel_times)
            for bn in  pair[1]:
                self.break_nodes[bn.node]=bn
                # print('checking',bn.origin,bn.node,bn.destination)
                assert int(travel_times.loc[bn.origin,bn.node]) == bn.tt_o
                assert int(travel_times.loc[bn.node,bn.destination]) == bn.tt_d

            new_node = len(travel_times.index)
            assert new_node > max(self.break_nodes.keys())

        print('Next deal with destinations crossed with all origins')

        # now do that for all destinations to all origins plus depot
        # (0). Yes, this can blow up quite large so only merge those that
        # are possible inside horizon given the total travel time


        new_node = len(travel_times.index)
        destination_details = []
        origin_details = []
        for idx in self.demand.index[feasible_index]:
            record = self.demand.loc[idx]
            destination_details.append((record.destination,
                                        record.earliest_destination,
                                        record.origin))
            origin_details.append((record.origin,
                                   record.late))
        #     # do_tt = travel_times.loc[0,record.origin]
        #     # do_breaks = (math.floor(do_tt/60/11)) * 60*10
        #     # do_total = do_tt + do_breaks
        #     # # origin_trip_cost = record['round_trip'] - do_total

        #     # od_tt = travel_times.loc[record.origin,record.destination]
        #     # od_breaks = (math.floor(do_tt/60/11)) * 60*10
        #     # od_total = od_tt + od_breaks

        #     # dd_tt = travel_times.loc[record.destination,0]
        #     # dd_breaks = (math.floor(dd_tt/60/11)) * 60*10
        #     # dd_total = dd_tt + dd_breaks
        #     # destination_trip_cost = record['round_trip'] - dd_total
        #     destinations.append[
        #     destination_details.append((record.destination,destination_trip_cost,record.origin,record.late+od_total))
        #     origin_details.append((record.origin,origin_trip_cost,record.destination,record.late))

        for dd in destination_details:
            didx = dd[0]
            moretimes = []
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
                moretimes.append(pair[0])
                for nn in pair[1]:
                    if self.debug:
                        print('add new node',nn.node,'bewteen',nn.origin,nn.destination)
                    self.break_nodes[nn.node] = nn
                new_node = pair[2]

            print(didx,'append',len(moretimes),'more')
            travel_times = breaks.aggregate_split_nodes(travel_times,moretimes)
        # print(len(self.break_nodes.keys()), len(travel_times.index))
        return travel_times # which holds everything of interest except self.break_nodes


    def get_break_node(self,node):
        return self.break_nodes[node]

    def breaks_at_nodes_constraints(self,
                                    num_veh,
                                    time_matrix,
                                    manager,
                                    routing,
                                    time_dimension,
                                    count_dimension,
                                    drive_dimension,
                                    drive_dimension_start_value):

        solver = routing.solver()
        for bn in self.break_nodes.values():
            origin_node = bn.origin
            destination_node = bn.destination
            break_node = bn.node
            tt_bd = bn.tt_d
            tt_ob = bn.tt_o
            tt = tt_bd + tt_ob
            tt_checked = time_matrix.loc[origin_node,destination_node]
            # print('origin node',origin_node,
            #       'break node',break_node,
            #       'next node',destination_node,
            #       'tt',tt,
            #       'tt_checked',tt_checked)

            # diagnosic prior to bombing out
            if(int(tt_checked) > 0):
                if math.floor(tt / int(tt_checked)) != 1:
                    print(time_matrix.loc[:,[origin_node,break_node,destination_node]])
                    print('origin node',origin_node,
                          'break node',break_node,
                          'next node',destination_node,
                          'tt',tt,
                          'tt_checked',tt_checked
                    )

                    assert math.floor(tt / int(tt_checked)) == 1
            else:
                assert math.floor(tt) == math.floor(tt_checked)
            o_idx = manager.NodeToIndex(origin_node)
            d_idx = manager.NodeToIndex(destination_node)
            b_idx = manager.NodeToIndex(break_node)

            # goal: if the trip from origin to destination happens,
            # decide if need to insert the break.

            # the trick is that we might not be going to destination
            # from origin, but rather from some other node.

            # so need to build up some conditions that guarantee that
            # we're going from origin to destination, *and* that given
            # that fact, that we need to incur this break or not

            # condition 1, same vehicle at origin and destination
            same_vehicle = routing.VehicleVar(o_idx) == routing.VehicleVar(d_idx)

            # condition 2, both nodes are active and sequential..harder to prove
            # try the count dimension, but they won't be sequential, and if there are
            # multiple breaks they will be 2 or more apart...
            dest_active =routing.ActiveVar(d_idx)
            origin_active =routing.ActiveVar(o_idx)
            break_active =routing.ActiveVar(b_idx)

            origin_count = routing.ActiveVar(o_idx)*count_dimension.CumulVar(o_idx)
            dest_count = dest_active*count_dimension.CumulVar(d_idx)

            dest_drive = dest_active*drive_dimension.CumulVar(d_idx)

            break_drive = break_active*drive_dimension.CumulVar(b_idx)

            # condition:  Does the origin immediately precede this node


            # get the break count.  actually, this is the wrong thing
            break_count = bn.break_count

            origin_break_condition = routing.ActiveVar(o_idx)*drive_dimension.CumulVar(o_idx) >= drive_dimension_start_value +  (660) - tt
            origin_nobreak_condition = routing.ActiveVar(o_idx)*drive_dimension.CumulVar(o_idx) <  drive_dimension_start_value + (660) - tt
            #print(origin_nobreak_condition)

            # if the origin node is a break node itself, might not need to visit
            if origin_node in self.break_nodes:
                # print('constraint from a break node',origin_node, drive_dimension_start_value + 2*(660) - tt)
                origin_break_condition = routing.ActiveVar(o_idx)*drive_dimension.CumulVar(o_idx) >= drive_dimension_start_value + 2*(660) - tt
                origin_nobreak_condition = routing.ActiveVar(o_idx)*drive_dimension.CumulVar(o_idx) < drive_dimension_start_value + 2*(660) - tt

            # else:
            #     print('constraint from a regular node',origin_node, drive_dimension_start_value + (660) - tt)

            active_break_o = routing.ActiveVar(b_idx) == routing.ActiveVar(o_idx)
            active_break_d = routing.ActiveVar(b_idx) == routing.ActiveVar(d_idx)
            skip_break = routing.ActiveVar(b_idx) == 0
            # if origin_node == 0:
            #     # can take some short cuts with the conditionals if
            #     # origin is depot node basically, if the travel time
            #     # is > 660, will need this break if visiting the node
            #     # with this vehicle from this depot
            #     #


            #     # constrain on destination
            #     # expression = solver.ConditionalExpression(origin_break_condition,
            #     #                                           active_break_d,
            #     #                                           1)
            #     # solver.AddConstraint(expression>=1)
            #     not_expression = solver.ConditionalExpression(same_vehicle*origin_nobreak_condition,
            #                                                   skip_break,
            #                                                   1)
            #     solver.AddConstraint(not_expression>=1)
            # else:
            #     # constrain on origin
            #     # expression = solver.ConditionalExpression(origin_break_condition,
            #     #                                           active_break_o,
            #     #                                           1)
            #     # solver.AddConstraint(expression>=1)
            #     not_expression = solver.ConditionalExpression(same_vehicle*origin_nobreak_condition,
            #                                                   skip_break,
            #                                                   1)
            #     solver.AddConstraint(not_expression>=1)

            #             # set condition


            # if not destination_node in self.break_nodes:
            #     solver.AddConstraint(dest_drive >= dest_active*drive_dimension_start_value)
            #     solver.AddConstraint(dest_drive <= dest_active*(drive_dimension_start_value + 660))
            # the next is redundant, I think
            # solver.AddConstraint(break_drive >= break_active*(drive_dimension_start_value - 660))

        feasible_index = self.demand.feasible
        for idx in self.demand.index[feasible_index]:
            record = self.demand.loc[idx,:]
            o_idx = manager.NodeToIndex(record.origin)
            d_idx = manager.NodeToIndex(record.destination)
            origin_active =routing.ActiveVar(o_idx)
            dest_active =routing.ActiveVar(d_idx)

            origin_drive = origin_active*drive_dimension.CumulVar(o_idx)
            dest_drive = dest_active*drive_dimension.CumulVar(d_idx)

            # this one on
            solver.AddConstraint(origin_drive >= origin_active*drive_dimension_start_value)

            # try this one off ?  need on for demand_12
            solver.AddConstraint(origin_drive < origin_active*(drive_dimension_start_value)+660)
            # try this one off?  haven't seen it triggered if left off, but
            # doesn't speed up the solution any either
            solver.AddConstraint(dest_drive >= dest_active*drive_dimension_start_value)

            # try this one on its own.
            solver.AddConstraint(dest_drive < dest_active*(drive_dimension_start_value)+660)

        # constraints on return to depot, otherwise we just collect
        # break nodes on the way back
        for veh in range(0,num_veh):
            index = routing.End(veh)
            end_drive = drive_dimension.CumulVar(index)
            solver.AddConstraint(
                end_drive >= drive_dimension_start_value)
