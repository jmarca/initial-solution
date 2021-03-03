from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from functools import partial

import solution_output as SO
import evaluators as E
import demand as D
import vehicles as V
import model_run as MR
import initial_routes as IR

import read_csv as reader

# hack to capture stdout to a string, to test it
import io, sys
from contextlib import contextmanager
import os
import filecmp

output_file = 'test_output.txt'
second_output_file = 'test_output_1.txt'
third_output_file = 'test_output_2.txt'
expected_file = 'test/data/expected_test_output.txt'
expected_breaks_file = 'test/data/expected_test_breaks_output.txt'

class MockArgs():

    def __init__(self):
        self.speed = 60
        self.summary_output = output_file

@contextmanager
def redirected(out=sys.stdout, err=sys.stderr):
    saved = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        yield
    finally:
        sys.stdout, sys.stderr = saved

def test_output():

    horizon = 20000
    m = reader.load_matrix_from_csv('test/data/matrix.csv')
    odpairs = reader.load_demand_from_csv('test/data/demand.csv')
    d     = D.Demand(odpairs,m,horizon)
    m = d.generate_solver_space_matrix(m)

    v = V.Vehicles(5,horizon)
    # (assignment,routing,manager) = MR.model_run_nobreaks3(d,m,v)
    (assignment,routing,manager) = MR.model_run_nobreaks(d,m,v.vehicles)

    assert assignment

    out = io.StringIO()
    err = io.StringIO()
    args = MockArgs()
    with redirected(out=out, err=err):
        out.flush()
        err.flush()
        SO.print_solution(d,m,m,
                          v,manager,routing,assignment,horizon,
                          0,args
        )
        output = out.getvalue()

        expected_output = ""
        assert output == expected_output
        assert filecmp.cmp(output_file,expected_file)

    # make sure output file was created as directed
    assert os.path.exists(args.summary_output)

    # write details again, and this time there should be a _1 version of args.summary_output
    assert not os.path.exists(second_output_file)
    SO.print_solution(d,m,m,
                      v,manager,routing,assignment,horizon,
                      0,args
    )
    # created alternate named file
    assert os.path.exists(second_output_file)
    assert filecmp.cmp(output_file,second_output_file)

    # now try again without the file

    out = io.StringIO()
    err = io.StringIO()
    args.summary_output = None
    with redirected(out=out, err=err):
        out.flush()
        err.flush()
        SO.print_solution(d,m,m,
                          v,manager,routing,assignment,horizon,
                          0,args
        )
        output = out.getvalue()

        f = open(expected_file, "r", encoding="utf-8")
        expected_output = f.read()
        assert output == expected_output

    assert not os.path.exists(third_output_file)

    os.unlink(output_file)
    os.unlink(second_output_file)
    # reset args to dump output file
    args = MockArgs()

    # test when run with breaks
    x_m = d.insert_nodes_for_breaks(m)
    trip_chains = IR.initial_routes_2(d,v.vehicles,x_m)
    initial_routes = [v for v in trip_chains.values()]
    (assignment,routing,manager) = MR.model_run(d, x_m, v.vehicles,
                                                10000, None, initial_routes)
    SO.print_solution(d,x_m,x_m,
                      v,manager,routing,assignment,horizon,
                      10000,args
    )

    assert filecmp.cmp(output_file,expected_breaks_file)
    os.unlink(output_file)
