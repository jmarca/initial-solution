import demand as D
import numpy as np
import read_csv as reader

def test_demand():
    horizon = 10000
    putime = 20
    dotime = 25
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    odpairs = reader.load_demand_from_csv('test/data/demand.csv')
    d     = D.Demand(odpairs,m,horizon)
    d_alt = D.Demand(odpairs,m,horizon*10,putime,dotime)

    assert (d.demand.early.min() > 0)
    assert (d.demand.early.max() < horizon)
    assert (d.demand.late.min() > 0)
    assert (d.demand.late.max() < horizon)

    # test that horizon weeded out OD pairs
    assert (len(d.equivalence) == 2)
    assert (len(d_alt.equivalence) == 10)

    listing = d.get_node_list()
    assert len(listing) == 2
    for i in listing:
        assert isinstance(i,np.int64)
    # print(d.demand.loc[:,['feasible','from_node','to_node','origin','destination']])
    assert d.get_map_node(0) == 0
    assert d.get_map_node(1) == 5 # first few are not feasible with short horizon
    assert d.get_map_node(2) == 2
    assert d.get_map_node(3) == -1 # only one pickup pair is feasible with short horizon



    # loading time is 15 as default
    assert d.get_service_time(1) == 15
    # unloading time is 15 as default
    assert d.get_service_time(2) == 15
    assert d.get_service_time(0) == 0
    assert d.get_service_time(3) == 0

    # loading time is 20 in alternate
    assert d_alt.get_service_time(1) == 20
    # unloading time is 25 in alternate
    assert d_alt.get_service_time(6) == 25  # and long horizon has more pairs


    # other functions tested in test_evaluators, as they involve other modules?
    node_list = d.get_node_list()
    assert node_list[0] == 1
    assert node_list[1] == 2

    assert d.get_demand_number(1) == 3
    assert d_alt.get_demand_number(1) == 0

    assert d.get_demand_number(2) == 3
    assert d.get_demand_number(0) == -1
    assert d.get_demand_number(3) == -1

    assert d.get_demand(0) == 0
    assert d.get_demand(1) == 1
    assert d.get_demand(2) == -1
    assert d.get_demand(3) == 0

    mm = d.generate_solver_space_matrix(m)
    assert mm.max().max() > 0
    assert len(mm.index) == 3
    assert mm.loc[0,0] == 0
    assert mm.loc[0,1] == 930
    assert np.isnan(mm.loc[0,2])

    mm = d_alt.generate_solver_space_matrix(m)
    assert mm.max().max() > 0
    assert len(mm.index) == 11 # 5 nodes plus depot
    assert mm.loc[0,0] == 0
    assert mm.loc[0,1] == 1150
    assert np.isnan(mm.loc[6,1])
    assert np.isnan(mm.loc[0,6])
    mm_ex = d_alt.insert_nodes_for_breaks(mm)
    for idx in mm.index:
        assert mm.loc[idx,idx] == mm_ex.loc[idx,idx]

    assert len(mm_ex.index) > len(mm.index)
    # travel times from new nodes to all nodes is less than max of original matrix
    new_nodes = range(len(mm.index),len(mm_ex.index))
    assert mm_ex.loc[new_nodes,:].max().max() < mm.max().max()
    # and all to new, ditto
    assert mm_ex.loc[:,new_nodes].max().max() < mm.max().max()

    break_chain = d_alt.get_break_node_chain(0,1)
    new_node_start = len(mm.index)
    assert len(break_chain) == 5
    assert break_chain[0] == new_node_start + 1
    assert break_chain[1] == new_node_start + 0
    assert break_chain[2] == new_node_start + 3
    assert break_chain[3] == new_node_start + 2
    assert break_chain[4] == new_node_start + 4

    assert d_alt.get_break_node(0) == None
    bn8 = d_alt.get_break_node(new_node_start)
    bn10 = d_alt.get_break_node(new_node_start+1)

    bn8.node = new_node_start
    bn8.origin = 0
    bn8.destination = bn10.node
    bn8.break_time = 30
    bn8.drive_time_restore = -480

    bn10.node = new_node_start + 1
    bn10.origin = 0
    bn10.destination = 1
    bn10.break_time = 600
    bn10.drive_time_restore = -660
