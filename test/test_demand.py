import demand as D

def test_demand():
    d     = D.Demand('test/data/demand.csv',10000)
    d_alt = D.Demand('test/data/demand.csv',10000,20,20)
