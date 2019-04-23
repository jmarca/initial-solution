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
    event_csv = pd.read_csv(filename)


    # do checks of data here

    return event_csv

def load_matrix_from_csv(filename):
    """extract a usable data structure from a csv file

    Args:
       filename (str): the input csv file to read.  will be read with pandas.read_csv(filename)

    Returns: a pandas.DataFrame you can use, or just save as json for future runs

    """
    matrix = pd.read_csv(filename,header=None)
    assert (matrix.ndim == 2)
    # assert (matrix.size == 100 * 100)
    # assert (matrix.iloc[0,0] == 0)
    # assert (matrix.iloc[0,1] == 875)
    # assert (matrix.iloc[1,0] == 874)
    return matrix

def travel_time(speed,matrix):
    """convert the distance matrix into a travel time matrix"""
    return matrix.copy().div(speed)

def make_simple_matrix(matrix):
    """ convert a square pandas data frame into a simple matrix """
    froms_length = matrix.iloc[:,0].size
    tos_length = matrix.iloc[0,:].size
    assert(froms_length == tos_length)
    number = froms_length
    distmat = np.zeros((number,number))
    for frm_idx in range(number):
        for to_idx in range(number):
            if frm_idx != to_idx:
                distmat[frm_idx,to_idx] = matrix.iloc[frm_idx,to_idx]
    # assert (distmat[0,1] == 875)
    # assert (distmat[1,0] == 874)
    return distmat
