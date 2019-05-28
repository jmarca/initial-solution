import read_csv as reader
import math

def test_load_demand():
    d = reader.load_demand_from_csv('test/data/demand.csv')
    assert (d.early.min() > 0)
    assert (d.early.max() < 10000)
    assert (d.late.min() > 0)
    assert (d.late.max() < 10000)
    assert (len(d) == 5)


def test_load_distance_matrix():
    matrix = reader.load_matrix_from_csv('test/data/matrix.csv')
    assert(matrix.ndim == 2)
    assert(matrix.size == 10*10)
    assert(matrix.loc[0,0] == 0)
    assert(matrix.loc[0,1] == 1269)
    assert(matrix.loc[1,0] == 1275)
    assert(matrix.loc[0].max() == 1842)
    assert(matrix.loc[:,0].max() == 1857)



def test_create_time_matrix():
    matrix = reader.load_matrix_from_csv('test/data/matrix.csv')
    hours_matrix = reader.travel_time(60,matrix)
    assert (hours_matrix.loc[0,0] == 0)
    assert (hours_matrix.loc[0,1] == math.floor(21.15))
    minutes_matrix = reader.travel_time(1,matrix)
    assert (minutes_matrix.loc[0,0] == 0)
    assert (minutes_matrix.loc[0,1] == 1269.0) # a mile a minute
