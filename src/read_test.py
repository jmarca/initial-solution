from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import argparse
#import os

import read_csv as reader
import vehicles as V
import demand as D

def main():
    """Entry point of the program."""
    parser = argparse.ArgumentParser(description='Solve assignment of truck load routing problem, give hours of service rules and a specified list of origins and destinations')
    parser.add_argument('-m,--matrixfile', type=str, dest='matrixfile',
                        help='CSV file for travel matrix (distances)')
    parser.add_argument('-d,--demandfile', type=str, dest='demand',
                        help='CSV file for demand pairs (origin, dest, time windows)')
    parser.add_argument('--speed', type=float, dest='speed', default=55.0,
                        help='Average speed, miles per hour.  Default is 55 (miles per hour).  Distance unit should match that of the matrix of distances.  The time part should be per hours')
    parser.add_argument('--maxtime', type=float, dest='horizon', default=10080,
                        help='Max time in minutes.  Default is 7 days, which is 10080 minutes..')

    parser.add_argument('-v,--vehicles', type=int, dest='numvehicles', default=100,
                        help='Number of vehicles to create.  Default is 100.')
    parser.add_argument('--pickup_time', type=int, dest='pickup_time', default=15,
                        help='Pick up time in minutes.  Default is 15 minutes.')
    parser.add_argument('--dropoff_time', type=int, dest='dropoff_time', default=15,
                        help='Drop off time in minutes.  Default is 15 minutes.')

    args = parser.parse_args()
    matrix = reader.load_matrix_from_csv(args.matrixfile)
    assert (matrix.ndim == 2)
    assert (matrix.size == 100 * 100)
    assert (matrix.iloc[0,0] == 0)
    assert (matrix.iloc[0,1] == 875)
    assert (matrix.iloc[1,0] == 874)
    # print(matrix.head())
    assert (len(matrix[0]) == 100)
    # will need a simple 2D array for calling into ortools...safer that way
    # dist_lookup = reader.make_simple_matrix(matrix)
    # print(dist_lookup[0,1])

    minutes_matrix = reader.travel_time(args.speed/60,matrix)
    # print(minutes_matrix.head())
    # tests?

    demand = D.Demand(args.demand,args.horizon)

    # print(demand.head())


    # vehicles:
    vehicles = V.Vehicles(args.numvehicles)

    # data is in, now process and setup solver

    # Create the routing index manager.
    # note that depot_index isn't an int, apparently.  have to cast
    # print(len(matrix), args.numvehicles, int(vehicles.vehicles[0].depot_index))
    manager = pywrapcp.RoutingIndexManager(
        len(matrix), args.numvehicles, int(vehicles.vehicles[0].depot_index))


if __name__ == '__main__':
    main()
