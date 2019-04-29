import evaluators as E
import demand as D
import read_csv as reader
import sys

class MockManager():

    def NodeToIndex(self,a):
        return a

    def IndexToNode(self,a):
        return a

def test_time_callback():

    horizon = 10000
    d = D.Demand('test/data/demand.csv',horizon)
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    m_m = reader.travel_time(1,m)


    demand_callback = E.create_demand_callback(d)

    dist_callback = E.create_dist_callback(m,d)

    manager = MockManager()

    assert demand_callback(manager,0) == 0
    assert demand_callback(manager,1) == 1
    assert demand_callback(manager,5) == 1
    assert demand_callback(manager,6) == -1

    # Time tests

    # simple time callback with original minutes matrix
    time_callback = E.create_time_callback(m_m,d)

    assert time_callback(manager,0,0) == 0
    # note that first line in demand is mapnode 7 to mapnode 9
    # so node 0 to node 1 is depot to node 7, is 1150
    assert time_callback(manager,0,1) == 1150.0 ## no pickup

    # now node 1 (map node 7 to node 2 (mapnode 5) has pickup time, so is 739 + 15
    assert time_callback(manager,1,2) == 739.0+15 ## with load time at 1

    # Distance tests, no pickup or dropoff times

    assert dist_callback(manager,0,0) == 0
    # Again that first line in demand is mapnode 7 to mapnode 9
    # so node 0 to node 1 is depot to node 7, is 1150 miles
    assert dist_callback(manager,0,1) == 1150.0

    # now node 1 (map node 7 to node 2 (mapnode 5), so is 739 miles
    assert dist_callback(manager,1,2) == 739.0 # no pickup or delivery add on


    # more extensive time callback with break nodes too
    m_m_more = d.make_break_nodes(m_m)
    time_callback = E.create_time_callback(m_m_more,d)

    assert time_callback(manager,0,0) == 0
    # note that first line in demand is mapnode 7 to mapnode 9
    # so node 0 to node 1 is depot to node 7, is 1150
    assert time_callback(manager,0,1) == 1150.0 ## no pickup

    # now node 1 (map node 7 to node 2 (mapnode 5) has pickup time, so is 739 + 15
    assert time_callback(manager,1,2) == 739.0+15 ## with load time at 1

    # so getting same results for original nodes.  now for obnoxious
    # break nodes, should not be any service times
    # first, pick off a simple break to break pair
    first_break_node = len(m_m[0])+1
    second_break_node = len(m_m[0])+2
    print(first_break_node,second_break_node)
    print(m_m_more.loc[[1,6,11,12,13],:])
    print(m_m_more.loc[[1,6,11,12,13],[1,6,11,12,13]])
    print(m_m_more.loc[1,11])
    assert m_m_more.loc[first_break_node,second_break_node] == 60
    assert m_m_more.loc[second_break_node,first_break_node] == sys.maxsize
    assert 0
