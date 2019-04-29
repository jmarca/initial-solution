import breaks as B
import demand as D
import read_csv as reader
import math

def test_make_nodes():

    # no new nodes with travel time equal to one hour
    origin = 10
    destination = 20
    travel_time = 60
    starting_node = 30
    new_tt_matrix = B.make_nodes(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 2
    assert new_tt_matrix == {10:{10:0,20:60},20:{20:0}}

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

    # now test the break generator
    # first read in the test demand
    horizon = 10000
    d     = D.Demand('test/data/demand.csv',horizon)
    # read in travel time
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    # assume a mile a minute (60mph), so m in miles === m in minutes

    gb = B.break_generator(m)
    # apply to demand
    newtimes = d.demand.apply(gb,axis=1,result_type='reduce')
    print(newtimes)
    assert len(newtimes) == len(d.demand)
    # check each row for reasonableness
    count_new_nodes = 0
    count_nodes = 0
    for idx in range(0,len(newtimes)):
        origin = d.demand.loc[idx,'origin']
        dest   = d.demand.loc[idx,'destination']
        nt = newtimes[idx]
        assert origin in nt.keys()
        assert dest in nt.keys()
        # check length
        tt = m.loc[d.demand.loc[idx,'from_node'],d.demand.loc[idx,'to_node']]
        expected_num_nodes = math.floor(tt/60)
        if tt % 60 == 0:
            expected_num_nodes -= 1
        assert len(nt) == expected_num_nodes + 2
        count_new_nodes += (len(nt) - 2)
        count_nodes += len(nt)

    # now test generating new travel time matrix
    new_tt = B.aggregate_time_matrix(m,newtimes)
    assert len(new_tt) == count_nodes

    assert new_tt.ndim == 2
    assert len(new_tt[0]) == count_nodes
