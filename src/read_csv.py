"""Read in the problem configuration from CSV"""

import pandas as pd
import numpy as np
import re


def extract_from_csv(filename):
    """extract a usable data structure from a csv file

    Args:
       filename (str): the input csv file to read.  will be read with pandas.read_csv(filename)

    Returns: a pandas.DataFrame you can use, or just save as json for future runs

    """
    event_csv = pd.read_csv(filename)


    # do checks of data here

    return event_csv
