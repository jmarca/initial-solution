import breaks as b

def test_make_nodes():

    # no new nodes with travel time equal to one hour
    origin = 10
    destination = 20
    travel_time = 60
    starting_node = 30
    new_tt_matrix = b.make_nodes(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 2
    assert new_tt_matrix == {10:{10:0,20:60},20:{20:0}}

    # one new node at 61 minutes
    travel_time = 61
    new_tt_matrix = b.make_nodes(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 3
    assert new_tt_matrix == {10:{10:0,20:61,30:60},20:{20:0},30:{30:0,20:1}}

    # one new node at 120 minutes
    travel_time = 120
    new_tt_matrix = b.make_nodes(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 3
    assert new_tt_matrix == {10:{10:0,20:120,30:60},20:{20:0},30:{30:0,20:60}}

    # two new nodes at 121 minutes
    travel_time = 121
    new_tt_matrix = b.make_nodes(origin,destination,travel_time,starting_node)
    assert len(new_tt_matrix) == 4 # O + D + 2 new nodes
    assert new_tt_matrix == {10:{10:0,20:121,30:60,31:120},
                             20:{20:0},
                             30:{30:0,31:60,20:61},
                             31:{31:0,20:1}
    }
