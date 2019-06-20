from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from functools import partial
import math
import numpy as np
import pickle

import argparse
#import os

import read_csv as reader
import vehicles as V
import demand as D
import evaluators as E
import solution_output as SO

import initial_routes as IR
import model_run as MR

def main():
    """Entry point of the program."""
    parser = argparse.ArgumentParser(description='Solve assignment of truck load routing problem, with specified list of origins and destinations, ignoring hours of service rules')
    # parser.add_argument('--resume_file',type=str,dest='resumefile',
    #                     help="resume a failed solver run from this file")
    parser.add_argument('-m,--matrixfile', type=str, dest='matrixfile',
                        help='CSV file for travel matrix (distances)')
    parser.add_argument('-d,--demandfile', type=str, dest='demand',
                        help='CSV file for demand pairs (origin, dest, time windows)')
    parser.add_argument('-o,--vehicleoutput', type=str, dest='vehicle_output', default='vehicle_output.csv',
                        help='CSV file for dumping output')
    parser.add_argument('--demandoutput', type=str, dest='demand_output', default='demand_output.csv',
                        help='CSV file for dumping output for demand details (including invalid demands, etc)')
    parser.add_argument('--summaryoutput', type=str, dest='summary_output',
                        help='A file for dumping the human-readable summary output for the assignment')
    parser.add_argument('--speed', type=float, dest='speed', default=55.0,
                        help='Average speed, miles per hour.  Default is 55 (miles per hour).  Distance unit should match that of the matrix of distances.  The time part should be per hours')
    parser.add_argument('--maxtime', type=int, dest='horizon', default=10080,
                        help='Max time in minutes.  Default is 10080 minutes, which is 7 days.')

    parser.add_argument('-v,--vehicles', type=int, dest='numvehicles', default=100,
                        help='Number of vehicles to create.  Default is 100.')
    parser.add_argument('--pickup_time', type=int, dest='pickup_time', default=15,
                        help='Pick up time in minutes.  Default is 15 minutes.')
    parser.add_argument('--dropoff_time', type=int, dest='dropoff_time', default=15,
                        help='Drop off time in minutes.  Default is 15 minutes.')

    parser.add_argument('-t, --timelimit', type=int, dest='timelimit', default=5,
                        help='Maximum run time for solver, in minutes.  Default is 5 minutes.')

    parser.add_argument('--initial_routes', type=bool, dest='initial_routes', default=False,
                        help="If true, generate initial routes.  Sometimes the solution isn't as good as letting the solver do its thing, but sometimes it is better.  In tests, with all 100 trips active it is slightly better to set initial routes, but with just 50 routes active, the solution is better without initial routes.")

    parser.add_argument('--narrow_destination_timewindows', type=bool,
                        dest='destination_time_windows',
                        default=True,
                        help="If true, limit destination node time windows based on travel time from corresponding origin.  If false, destination nodes time windows are 0 to args.horizon.  Default true (limit the time window).")

    parser.add_argument('--debug', type=bool, dest='debug', default=False,
                        help="Turn on some print statements.")

    args = parser.parse_args()

    print('read in distance matrix')
    matrix = reader.load_matrix_from_csv(args.matrixfile)
    minutes_matrix = reader.travel_time(args.speed/60,matrix)

    print('read in demand data')
    odpairs = reader.load_demand_from_csv(args.demand)
    d = D.Demand(odpairs,minutes_matrix,args.horizon,use_breaks=False)

    # convert nodes to solver space from input map space
    expanded_mm = d.generate_solver_space_matrix(minutes_matrix,args.horizon)

    # echo nodes to distance matrix
    expanded_m = reader.travel_time(60/args.speed,expanded_mm)
    # print('original matrix of',len(matrix.index),'expanded to ',len(expanded_m.index))

    # vehicles:
    vehicles = V.Vehicles(args.numvehicles,args.horizon)

    # number of nodes is now given by the travel time matrix
    # probably should refactor to put time under control of
    # demand class
    num_nodes = len(expanded_mm.index)
    print('Solving with ',num_nodes,'nodes')
    print(d.demand.loc[:,['from_node',
                          'to_node',
                          'early',
                          'late',
                          'pickup_time',
                          'dropoff_time',
                          'round_trip',
                          'depot_origin',
                          'earliest_destination',
                          'feasible',
                          'origin',
                          'destination']])


    initial_routes = None
    trip_chains = {}
    assignment=None
    routing=None
    manager=None
    if args.initial_routes:
        trip_chains = IR.initial_routes_no_breaks(d,vehicles.vehicles,expanded_mm,
                                                  debug = args.debug)
        initial_routes = [v for v in trip_chains.values()]
        (assignment,routing,manager) = MR.model_run_nobreaks(d,expanded_mm,vehicles.vehicles,
                                                             None,initial_routes,
                                                             args)
    else:
        (assignment,routing,manager) = MR.model_run_nobreaks(d,expanded_mm,vehicles.vehicles,
                                                             args=args)

    if assignment:
        ## save the assignment, (Google Protobuf format)
        #save_file_base = os.path.realpath(__file__).split('.')[0]
        #if routing.WriteAssignment(save_file_base + '_assignment.ass'):
        #    print('succesfully wrote assignment to file ' + save_file_base +
        #          '_assignment.ass')

        #print(expanded_mm)
        print('The Objective Value is {0}'.format(assignment.ObjectiveValue()))
        print('details:')

        SO.print_solution(d,expanded_m,expanded_mm,
                          vehicles,manager,routing,assignment,args.horizon,
                          0,
                          args)
        SO.csv_output(d,expanded_m,expanded_mm,
                      vehicles,manager,routing,assignment,args.horizon,
                      args.vehicle_output)
        SO.csv_demand_output(d,expanded_m,expanded_mm,
                             vehicles,manager,routing,assignment,args.horizon,
                             args.demand_output)

    else:
        print('assignment failed')



if __name__ == '__main__':
    main()
