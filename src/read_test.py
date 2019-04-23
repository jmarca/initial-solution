import argparse
import read_csv as reader
import os

def main():
    """Entry point of the program."""
    parser = argparse.ArgumentParser(description='Solve assignment of truck load routing problem, give hours of service rules and a specified list of origins and destinations')
    parser.add_argument('-m,--matrixfile', type=str, dest='matrixfile',
                        help='CSV file for travel matrix (distances)')
    parser.add_argument('-d,--demandfile', type=str, dest='demand',
                        help='CSV file for demand pairs (origin, dest, time windows)')

    args = parser.parse_args()
    matrix = reader.load_matrix_from_csv(args.matrixfile)
    print(matrix.head())
    # dist_lookup = reader.make_simple_matrix(matrix)
    # print(dist_lookup[0,1])

    time_matrix = reader.travel_time(1/60,matrix)
    print(time_matrix.head())
if __name__ == '__main__':
    main()
