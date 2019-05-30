import breaks as B
import demand as D
import read_csv as reader
import math
import pandas as pd
import numpy as np

def test_make_nodes():

    # no new nodes with travel time equal to one hour
    origin = 10
    destination = 20
    travel_time = 60
    starting_node = 30
    new_tt_matrix = B.make_nodes(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 2
    assert new_tt_matrix == {10:{10:0,20:60},20:{20:0}}

    # check that pandas reads that in correctly
    df = pd.DataFrame.from_dict(new_tt_matrix,orient='index')
    assert df.loc[10,10] == 0
    assert df.loc[10,20] == 60


    # ditto, but specifying timelength of 90
    origin = 10
    destination = 20
    travel_time = 90
    starting_node = 30
    new_tt_matrix = B.make_nodes(origin,destination,travel_time,starting_node,90)
    assert len(new_tt_matrix) == 2
    assert new_tt_matrix == {10:{10:0,20:90},20:{20:0}}


    # one new node at 61 minutes
    travel_time = 61
    new_tt_matrix = B.make_nodes(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 3
    assert new_tt_matrix == {10:{10:0,20:61,30:60},20:{20:0},30:{30:0,20:1}}

    # one new node at 120 minutes
    travel_time = 120
    new_tt_matrix = B.make_nodes(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 3
    assert new_tt_matrix == {10:{10:0,20:120,30:60},20:{20:0},30:{30:0,20:60}}

    # two new nodes at 121 minutes
    travel_time = 121
    new_tt_matrix = B.make_nodes(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 4 # O + D + 2 new nodes
    assert new_tt_matrix == {10:{10:0,20:121,30:60,31:120},
                             20:{20:0},
                             30:{30:0,31:60,20:61},
                             31:{31:0,20:1}
    }

    # test split_links

def test_split_links():

    # split links in half, insert a new node
    origin = 10
    destination = 20
    travel_time = 60
    starting_node = 30
    new_tt_matrix = B.split_links(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 3
    assert new_tt_matrix == {10:{10:0,20:60,30:30},20:{20:0},30:{20:30,30:0}}

    # check that pandas reads that in correctly
    df = pd.DataFrame.from_dict(new_tt_matrix,orient='index')
    assert df.loc[10,10] == 0
    assert df.loc[10,20] == 60
    assert df.loc[10,30] == 30
    assert df.loc[30,20] == 30
    assert np.isnan(df.loc[20,30])


def test_split_links_break_nodes():

    # split up a link as needed for breaks
    origin = 10
    destination = 20
    travel_time = 61
    starting_node = 30
    break_time = 123
    reset_time = 456
    pair = B.split_links_break_nodes(origin,destination,
                                     travel_time,
                                     starting_node,
                                     break_time=break_time,
                                     reset_time=reset_time)
    assert len(pair) == 2
    new_times = pair[0]
    # times should be a numpy array
    assert len(new_times) == 3
    assert len(new_times[0]) == 3
    assert new_times[0][0] == origin
    assert new_times[0][1] == starting_node
    assert int(new_times[0][2]) == 30

    assert new_times[1][0] == starting_node
    assert new_times[1][1] == starting_node
    assert int(new_times[1][2]) == 0

    assert new_times[2][0] == starting_node
    assert new_times[2][1] == destination
    assert int(new_times[2][2]) == 31

    # now inspect the break node object
    break_node = pair[1]
    assert break_node.origin == origin
    assert break_node.destination == destination
    assert break_node.node == starting_node
    assert break_node.break_time == break_time
    assert break_node.accumulator_reset == reset_time
    assert break_node.drive_time_restore() == -reset_time
    assert break_node.tt_o == 30
    assert break_node.tt_d == 31

def test_break_node_splitter():

    origin = 10
    destination = 20
    travel_time = 61
    starting_node = 30
    triple = B.break_node_splitter(origin,destination,travel_time,starting_node)
    assert len(triple)==3
    new_times = triple[0]
    assert len(new_times) == 7 # 3 for long break, 4 for short break
    assert new_times[0][0] == origin
    assert new_times[0][1] == starting_node
    assert int(new_times[0][2]) == 30

    assert new_times[1][0] == starting_node
    assert new_times[1][1] == starting_node
    assert int(new_times[1][2]) == 0

    assert new_times[2][0] == starting_node
    assert new_times[2][1] == destination
    assert int(new_times[2][2]) == 31

    # now the 8 hr break node
    assert new_times[3][0] == origin
    assert new_times[3][1] == starting_node+1
    assert int(new_times[3][2]) == 15

    assert new_times[4][0] == starting_node+1
    assert new_times[4][1] == starting_node+1
    assert int(new_times[4][2]) == 0

    assert new_times[5][0] == starting_node+1
    assert new_times[5][1] == starting_node
    assert int(new_times[5][2]) == 15

    # and the link to the destination too
    assert new_times[6][0] == starting_node+1
    assert new_times[6][1] == destination
    assert int(new_times[6][2]) == 46


    break_nodes = triple[1]
    assert len(break_nodes)==2 # one long break, one short break

    next_new_node = triple[2]
    assert next_new_node == starting_node + 2

def test_split_break_node():

    origin = 10
    destination = 20
    travel_time = 61
    starting_node = 30
    triple = B.break_node_splitter(origin,destination,travel_time,starting_node)
    assert len(triple)==3
    new_times = triple[0]
    assert len(new_times) == 7 # 3 for long break, 4 for short break
    assert new_times[0][0] == origin
    assert new_times[0][1] == starting_node
    assert int(new_times[0][2]) == 30

    assert new_times[1][0] == starting_node
    assert new_times[1][1] == starting_node
    assert int(new_times[1][2]) == 0

    assert new_times[2][0] == starting_node
    assert new_times[2][1] == destination
    assert int(new_times[2][2]) == 31

    # now the 8 hr break node
    assert new_times[3][0] == origin
    assert new_times[3][1] == starting_node+1
    assert int(new_times[3][2]) == 15

    assert new_times[4][0] == starting_node+1
    assert new_times[4][1] == starting_node+1
    assert int(new_times[4][2]) == 0

    assert new_times[5][0] == starting_node+1
    assert new_times[5][1] == starting_node
    assert int(new_times[5][2]) == 15

    # and the link to the destination too
    assert new_times[6][0] == starting_node+1
    assert new_times[6][1] == destination
    assert int(new_times[6][2]) == 46


    break_nodes = triple[1]
    assert len(break_nodes)==2 # one long break, one short break

    next_new_node = triple[2]
    assert next_new_node == starting_node + 2

def test_insert_nodes_for_breaks():

    # now test the break generator inside demand
    # first read in the test demand
    horizon = 10000
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    odpairs = reader.load_demand_from_csv('test/data/demand.csv')
    d     = D.Demand(odpairs,m,horizon)
    # read in travel time
    # assume a mile a minute (60mph), so m in miles === m in minutes
    # convert to solver space
    m = d.generate_solver_space_matrix(m)
    # this should drastically trim travel matrix, since only one
    # demand is feasible before 10000
    assert len(m) == 3
    newtimes = d.insert_nodes_for_breaks(m)
    assert len(newtimes) > len(m)
    # expect to have added 4 nodes between 0-1, 5 nodes between 1-2, 2
    # nodes 2-0 plus original 2
    assert len(newtimes) == 11 + 3

    # check each row for reasonableness
    count_new_nodes = 0
    count_nodes = 0
    feasible_index = d.demand.feasible
    for idx in d.demand.index[feasible_index]:
        print(idx)
        origin = d.demand.loc[idx,'origin']
        dest   = d.demand.loc[idx,'destination']
        print(origin,dest,idx)
        # 5 nodes link to origin---depot plus 4 break nodes
        assert len(newtimes.loc[:,origin].index[newtimes.loc[:,origin].notna()]) == 5
        # 6 nodes link to destination---origin plus 5 break nodes
        assert len(newtimes.loc[:,dest].index[newtimes.loc[:,dest].notna()]) == 6
