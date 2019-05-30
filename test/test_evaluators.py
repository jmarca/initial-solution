import evaluators as E
import demand as D
import read_csv as reader
import sys
import numpy as np
from functools import partial

class MockManager():

    def NodeToIndex(self,a):
        return a

    def IndexToNode(self,a):
        return a

def test_time_callback():
    pickup_time = 20
    dropoff_time = 10
    horizon = 10000
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    odpairs = reader.load_demand_from_csv('test/data/demand.csv')
    d     = D.Demand(odpairs,m,horizon,pickup_time=pickup_time,dropoff_time=dropoff_time)
    max_distance = m.max().max()
    m_m = reader.travel_time(1,m)
    max_time = m_m.max().max()

    # test fixing travel time matrix into model space
    m_m = d.generate_solver_space_matrix(m_m)
    assert m_m.ndim == 2
    # did I get it right?  the time from
    # node 0 to node 1 is depot to node 5, is 930
    assert m_m.loc[0,1] == m.loc[0,d.get_map_node(1)]





    # with horizon of 10000, only one OD pair is feasible
    assert len(m_m.index) == 3 # 2 nodes, 1 depot
    assert len(m_m.loc[0]) == 3

    demand_callback = E.create_demand_callback(m.index,d)

    manager = MockManager()

    assert demand_callback(manager,0) == 0
    assert demand_callback(manager,1) == 1
    assert demand_callback(manager,2) == -1
    assert demand_callback(manager,3) == 0

    # Distance tests, no pickup or dropoff times
    dist_callback = E.create_dist_callback(m_m,d)

    assert dist_callback(manager,0,0) == 0 # depot to depot is zero
    # Again that first line in demand is mapnode 7 to mapnode 9
    # so node 0 to node 1 is depot to node 7, is 930
    assert dist_callback(manager,0,1) ==  m.loc[0,d.get_map_node(1)]
    assert dist_callback(manager,1,2) ==  m.loc[d.get_map_node(1),d.get_map_node(2)]
    assert dist_callback(manager,2,0) ==  m.loc[d.get_map_node(2),0]
    # everything else is forbidden
    assert dist_callback(manager,0,2) > max_distance # can't skip pickup
    assert dist_callback(manager,2,1) > max_distance # can't go backwards
    assert dist_callback(manager,1,0) > max_distance # can't skip dropoff


    # Time tests add pickup and delivery time

    # simple time callback with original minutes matrix
    time_callback = E.create_time_callback2(m_m,d)

    assert time_callback(manager,0,0) == 0
    # note that pickup time at node, dropoff time at node is transit
    # time across node, so is only added in when node is origin
    assert time_callback(manager,0,1) ==  m.loc[0,d.get_map_node(1)]
    assert time_callback(manager,1,2) ==  m.loc[d.get_map_node(1),d.get_map_node(2)]+pickup_time
    assert time_callback(manager,2,0) ==  m.loc[d.get_map_node(2),0]+dropoff_time
    # everything else is forbidden
    assert time_callback(manager,0,2) > max_time # can't skip pickup
    assert time_callback(manager,2,1) > max_time # can't go backwards
    assert time_callback(manager,1,0) > max_time # can't skip dropoff



    # more extensive time callback with break nodes too
    m_m_more = d.insert_nodes_for_breaks(m_m)

    print('len m_m_more is ',len(m_m_more))

    assert len(m_m_more) > len(m_m)
    time_callback = E.create_time_callback2(m_m_more,d)
    # the following are same as above, should not have changed
    assert time_callback(manager,0,0) == 0
    assert time_callback(manager,0,1) ==  m.loc[0,d.get_map_node(1)]
    assert time_callback(manager,1,2) ==  m.loc[d.get_map_node(1),d.get_map_node(2)]+pickup_time
    assert time_callback(manager,2,0) ==  m.loc[d.get_map_node(2),0]+dropoff_time
    assert time_callback(manager,0,2) > max_time # can't skip pickup
    assert time_callback(manager,2,1) > max_time # can't go backwards
    assert time_callback(manager,1,0) > max_time # can't skip dropoff

    # now test new nodes, 3+
    assert len(m_m_more.index) == 14

    # test long break from 0 to 1
    assert time_callback(manager,0,3) ==  660
    # short break
    assert time_callback(manager,0,4) ==  480
    # short break happens
    assert time_callback(manager,4,3) ==  (660 - 480) + 30
    # long break happens
    assert time_callback(manager,3,1) ==  (m.loc[0,d.get_map_node(1)] - 660) + 600
    # can't go
    assert time_callback(manager,3,4) > max_time

    # test the drive callback accumulator
    drive_callback = partial(E.create_drive_callback(m_m_more,
                                                     d,
                                                     11*60,
                                                     10*60),
                             manager)

    # drive callback is just the drive time, but gets reset at long breaks
    bn11 = d.get_break_node(3)
    assert bn11.drive_time_restore() == -660

    assert drive_callback(0,0) == 0
    # no pickup, no dropoff time added to drive dimension
    assert drive_callback(0,1) ==  m.loc[0,d.get_map_node(1)]
    assert drive_callback(1,2) ==  m.loc[d.get_map_node(1),d.get_map_node(2)]
    assert drive_callback(2,0) ==  m.loc[d.get_map_node(2),0]
    assert drive_callback(0,2) > max_time # can't skip pickup
    assert drive_callback(2,1) > max_time # can't go backwards
    assert drive_callback(1,0) > max_time # can't skip dropoff

    # now test break nodes
    # test long break from 0 to 1
    assert drive_callback(0,3) ==  660 # just drive, haven't taken break
    # short break
    assert drive_callback(0,4) ==  480 # just drive, haven't taken break
    # short break happens, no impact
    assert drive_callback(4,3) ==  (660 - 480) # no 30 minute break added
    # long break happens
    assert drive_callback(3,1) ==  (m.loc[0,d.get_map_node(1)] - 660) + bn11.drive_time_restore()
    # can't go
    assert drive_callback(3,4) > max_time



    # now short break callback
    short_callback = partial(E.create_short_break_callback(m_m_more,
                                                           d,
                                                           8*60,
                                                           30),
                             manager)

    # drive callback is just the drive time, but gets reset at long breaks
    bn8 = d.get_break_node(4)
    assert bn8.drive_time_restore() == -480
    assert short_callback(0,0) == 0
    # no pickup, no dropoff time added to drive dimension
    assert short_callback(0,1) ==  m.loc[0,d.get_map_node(1)]
    assert short_callback(1,2) ==  m.loc[d.get_map_node(1),d.get_map_node(2)]
    assert short_callback(2,0) ==  m.loc[d.get_map_node(2),0]
    assert short_callback(0,2) > max_time # can't skip pickup
    assert short_callback(2,1) > max_time # can't go backwards
    assert short_callback(1,0) > max_time # can't skip dropoff

    # now test break nodes
    # test long break from 0 to 1
    assert short_callback(0,3) ==  660 # just drive, haven't taken break
    # short break
    assert short_callback(0,4) ==  480 # just drive, haven't taken break
    # short break happens, triggers restore of 480
    assert short_callback(4,3) ==  (660 - 480) + bn8.drive_time_restore()
    # long break happens.  Okay, the source code is lame, but it also restores 660 - 480
    assert short_callback(3,1) ==  (m.loc[0,d.get_map_node(1)] - 660) + (bn11.drive_time_restore() - bn8.drive_time_restore())
    # can't go
    assert short_callback(3,4) > max_time
