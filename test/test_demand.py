import demand as D
import numpy as np

def test_demand():
    horizon = 10000
    putime = 20
    dotime = 25
    d     = D.Demand('test/data/demand.csv',horizon)
    d_alt = D.Demand('test/data/demand.csv',horizon,putime,dotime)

    assert (d.demand.early.min() > 0)
    assert (d.demand.early.max() < horizon)
    assert (d.demand.late.min() > 0)
    assert (d.demand.late.max() < horizon)

    assert (len(d.equivalence) == 10)

    listing = d.get_node_list()
    assert len(listing) == 10
    for i in listing:
        assert isinstance(i,np.int64)

    assert d.get_number_nodes() == 10

    assert d.get_map_node(0) == 0

    assert d.get_map_node(1) == 7
    assert d.get_map_node(6) == 9

    # loading time is 15 as default
    assert d.get_service_time(1) == 15
    # unloading time is 15 as default
    assert d.get_service_time(6) == 15

    # loading time is 20 in alternate
    assert d_alt.get_service_time(1) == 20
    # unloading time is 25 in alternate
    assert d_alt.get_service_time(6) == 25

    # test making a demand map
    dm = d.get_demand_map()
    assert len(dm) == 10
    assert not (0 in dm.keys())
    assert 1 in dm.keys()
    assert 1 == dm[1]
    assert 6 in dm.keys()
    assert -1 == dm[6]

    # other functions tested in test_evaluators, as they involve other modules
