from collections import namedtuple
import pandas as pd
import numpy as np

class Vehicles():
  """
    A Class to create and hold vehicle information.
    Args:
    filename: the CSV file that defines the vehicles
    num_vehicles: default to 100, only used if filename is None
  """

  def __init__(self,
               # filename = None, # uncomment if want vehicle def in file
               num_vehicles,
               horizon
  ):
    # copy the python from the example.
    Vehicle = namedtuple(
      'Vehicle',
      [
        'index',
        'capacity',
        'cost',
        'time_window',
        'depot_index'
      ]
    )

    # if( filename != None ):
    #     vehs = pd.read_csv(filename)
    # else:
    # keep it simple.  just make a lot of vehicles with depot of zero
    # depot node 0, cost 1000, capacity 1 (keep it simple, but not too simple)
    # generally copy code from ortools example.
    idxs = np.array(range(0, num_vehicles))
    # all capacities are 1---truckload problem
    caps =  np.ones_like(idxs)
    # all costs are 1000---want to use the fewest possible
    costs =  1000*np.ones_like(idxs)
    # for now, all depots are index 0
    depots = np.zeros_like(idxs)
    # for now, all time windows are from 0 to horizon

    self.vehicles = [
          Vehicle(int(idx), int(capacity), int(cost), [0,horizon], int(depot_idx))
          for idx, capacity, cost, depot_idx in zip(idxs, caps, costs, depots)
      ]
