import evaluators as E
import demand as D
import read_csv as reader
import sys
import numpy as np

class MockManager():

    def NodeToIndex(self,a):
        return a

    def IndexToNode(self,a):
        return a

def test_time_callback():

    horizon = 10000
    d = D.Demand('test/data/demand.csv',horizon)
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    max_distance = m.max().max()
    m_m = reader.travel_time(1,m)
    max_time = m_m.max().max()

    # test fixing travel time matrix into model space
    m_m = d.generate_solver_space_matrix(m_m)
    assert m_m.ndim == 2
    assert len(m_m.index) == 11 # 10 nodes, 1 depot
    assert len(m_m.loc[0]) == 11
    # did I get it right?  the time from
    # node 0 to node 1 is depot to node 7, is 1150
    assert m_m.loc[0,1] == 1150.0

    # ditto with distance matrix, although that is only used to dump
    # output right now
    m = d.generate_solver_space_matrix(m)



    demand_callback = E.create_demand_callback(m.index,d)

    manager = MockManager()

    assert demand_callback(manager,0) == 0
    assert demand_callback(manager,1) == 1
    assert demand_callback(manager,5) == 1
    assert demand_callback(manager,6) == -1

    # Distance tests, no pickup or dropoff times
    dist_callback = E.create_dist_callback(m,d)

    assert dist_callback(manager,0,0) == 0 # depot to depot is zero
    # Again that first line in demand is mapnode 7 to mapnode 9
    # so node 0 to node 1 is depot to node 7, is 1150 miles
    assert dist_callback(manager,0,1) == 1150.0

    # now node 1 (map node 7 to node 2 (mapnode 5), so is 739 miles
    assert dist_callback(manager,1,2) > max_distance # never go from node 1 to node 2
    assert dist_callback(manager,1,6) == 810 # demand row 0, from 7 to 9
    assert dist_callback(manager,6,1) > max_distance # can't go backwards
    assert dist_callback(manager,6,0) < max_distance # can go from dest to depot
    assert dist_callback(manager,6,2) < max_distance # can go from dest to all origins
    assert dist_callback(manager,6,3) < max_distance # can go from dest to all origins
    assert dist_callback(manager,6,4) < max_distance # can go from dest to all origins
    assert dist_callback(manager,6,5) < max_distance # can go from dest to all origins

    # Time tests

    # simple time callback with original minutes matrix
    time_callback = E.create_time_callback(m_m,d)

    assert time_callback(manager,0,0) == 0
    # Again that first line in demand is mapnode 7 to mapnode 9
    # so node 0 to node 1 is depot to node 7, is 1150 miles
    print(m_m.loc[0,1])
    assert time_callback(manager,0,1) == 1150.0

    # now node 1 (map node 7 to node 2 (mapnode 5), so is 739 miles
    print(m_m.loc[1,2])
    assert time_callback(manager,1,2) > max_time # never go from node 1 to node 2
    assert time_callback(manager,1,6) == 825 # 810 demand row 0, from 7 to 9 + 15 service
    assert time_callback(manager,6,1) > max_time # can't go backwards
    assert time_callback(manager,6,0) < max_time # can go from dest to depot
    assert time_callback(manager,6,2) < max_time # can go from dest to all origins
    assert time_callback(manager,6,3) < max_time # can go from dest to all origins
    assert time_callback(manager,6,4) < max_time # can go from dest to all origins
    assert time_callback(manager,6,5) < max_time # can go from dest to all origins


    # more extensive time callback with break nodes too
    m_m_more = d.make_break_nodes(m_m)
    print('len m_m_more is ',len(m_m_more))

    assert len(m_m_more) > len(m_m)
    time_callback = E.create_time_callback(m_m_more,d)


    assert time_callback(manager,0,0) == 0
    # note that first line in demand is mapnode 7 to mapnode 9
    # so node 0 to node 1 is depot to node 7, is 1150
    assert time_callback(manager,0,1) == 1150.0 ## no pickup

    # now node 1 (map node 7 to node 2 (mapnode 5) has pickup time, so is 739 + 15
    assert time_callback(manager,1,2) > max_time # never go from node 1 to node 2
    assert time_callback(manager,1,6) == 825 # 810 demand row 0, from 7 to 9 + 15 service
    assert time_callback(manager,6,1) > max_time # can't go backwards
    assert time_callback(manager,6,0) < max_time # can go from dest to depot
    assert time_callback(manager,6,2) < max_time # can go from dest to all origins
    assert time_callback(manager,6,3) < max_time # can go from dest to all origins
    assert time_callback(manager,6,4) < max_time # can go from dest to all origins
    assert time_callback(manager,6,5) < max_time # can go from dest to all origins


    # so getting same results for original nodes.  now for obnoxious
    # break nodes, should not be any service times
    # first, pick off a simple break to break pair
    first_break_node = len(m_m[0])+1
    second_break_node = len(m_m[0])+2

    assert m_m_more.loc[first_break_node,second_break_node] == 60
    assert np.isnan(m_m_more.loc[second_break_node,first_break_node] )

    assert time_callback(manager,first_break_node,second_break_node) == 60
    assert time_callback(manager,second_break_node,first_break_node) > max_time

    assert time_callback(manager,1,first_break_node) == 60+15 # with pickup delay
    assert time_callback(manager,1,second_break_node) == 120+15 # with pickup delay
