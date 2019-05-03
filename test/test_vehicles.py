import vehicles as V

def test_vehicles():

    v = V.Vehicles(5,100)

    assert len(v.vehicles) == 5
    for idx in range(0,5):
        veh = v.vehicles[idx]
        assert veh.index == idx
        assert veh.capacity == 1
        assert veh.cost == 1000 # but this is unused at the moment
        assert veh.time_window[0] == 0
        assert veh.time_window[1] == 100 # no more default time window
        assert veh.depot_index == 0 # all vehicles are at depot 0 for now

    v2 = V.Vehicles(horizon=1000,num_vehicles=100) # test set horizon, default of 100 vehicles
    assert len(v2.vehicles) == 100
    for veh in v2.vehicles:
        assert veh.time_window[1] == 1000
