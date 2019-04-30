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
    # convert to solver space
    m = d.generate_solver_space_matrix(m)
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
        print(origin,dest,idx)
        assert origin in nt.keys()
        assert dest in nt.keys()
        # check length
        tt = m.loc[origin,dest]
        expected_num_nodes = math.floor(tt/60)
        if tt % 60 == 0:
            expected_num_nodes -= 1
        assert len(nt) == expected_num_nodes + 2
        count_new_nodes += (len(nt) - 2)
        count_nodes += len(nt)
        print(idx,origin,dest,tt,count_nodes,count_new_nodes)
    # now test generating new travel time matrix
    print(newtimes)
    new_tt = B.aggregate_time_matrix(m,newtimes)
    print(new_tt.loc[[0,1,6,12,13,14],[0,1,6,12,13,14]])
    assert len(new_tt) == count_nodes + 1 # account for depot node too

    assert new_tt.loc[12,13] == 60
    assert new_tt.loc[d.demand.loc[0,'origin'],12] == 60
    assert new_tt.loc[d.demand.loc[0,'origin'],13] == 120
    assert new_tt.ndim == 2
    assert len(new_tt[0]) == count_nodes + 1

    # now test that I can do that for all destinations+depot to all
    # origins+depot and append some more
    moretimes = []
    destinations_idx = [idx for idx in d.destinations.index]
    destinations_idx.append(0) # tack on the depot node
    origins_idx = [idx for idx in d.origins.index]
    origins_idx.append(0) # tack on the depot node
    new_node = len(new_tt)+1
    for didx in destinations_idx:
        for oidx in origins_idx:
            if oidx == didx:
                # depot to depot is silly
                continue
            tt = m.loc[didx,oidx]
            if (not np.isnan(tt)) and  tt > 60:
                print('call with',didx,oidx,tt,new_node)
                new_times = B.make_nodes(didx,oidx,tt,new_node)

                # test results
                assert oidx in new_times.keys()
                assert didx in new_times.keys()
                # check length
                expected_num_nodes = math.floor(tt/60)
                if tt % 60 == 0:
                    expected_num_nodes -= 1
                assert len(new_times) == expected_num_nodes + 2
                count_new_nodes += (len(new_times) - 2)
                count_nodes += len(new_times) - 2 # need -2 this time, as repeating O, D
                moretimes.append(new_times)

    new_tt = B.aggregate_time_matrix(new_tt,moretimes)
    assert len(new_tt) == count_nodes + 1
    assert new_tt.ndim == 2
    assert len(new_tt[0]) == count_nodes + 1
