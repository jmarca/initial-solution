"""Read in the problem configuration from CSV"""

import pandas as pd
import numpy as np
import re


def load_demand_from_csv(filename):
    """extract a usable data structure from a csv file

    Args:
       filename (str): the input csv file to read.  will be read with pandas.read_csv(filename)

    Returns: a pandas.DataFrame you can use, or just save as json for future runs

    """

    demand = pd.read_csv(filename,names=['from_node','to_node','early','late'],header=0)

    return demand

def load_matrix_from_csv(filename):
    """extract a usable data structure from a csv file

    Args:
       filename (str): the input csv file to read.  will be read with pandas.read_csv(filename)

    Returns: a pandas.DataFrame you can use, or just save as json for future runs

    """
    matrix = pd.read_csv(filename,header=None)
    return matrix

def travel_time(speed,matrix):
    """convert the distance matrix into a travel time matrix"""
    return matrix.copy().floordiv(speed)
