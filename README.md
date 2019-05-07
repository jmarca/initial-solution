# Open Solver Initial Solution

This solver generates an initial solution to the problem of routing
freight vehicles between cities while still respecting Hours
of Service (HOS) regulations.   The vehicles are fully loaded, meaning
it is a Truck Load Routing problem, with trucks having only one
delivery point for their full load.

The python code here reads in the CSV input file, sets up a call to Google's
OR-Tools routing solver, and then writes out that solution as a CSV
file.  While hopefully this initial solution is pretty good, it is the
job of downstream solvers to read in this initial solution and improve it.

# Docker setup

This project is easiest to run from within the Docker container that
can be build based on the Dockerfile.  To do this, change into the
Docker directory and execute the build command:

```
docker build -t jmarca/initial_solution .
```

This will build an image based on the official Python Docker image
that includes the latest version of OR Tools [version 7.0 at this
time](https://github.com/google/or-tools/releases/tag/v7.0).

To use the solver in this image, you have to create a container and
tell it how to find your data and code.  From the root of this
project, you can do this:

```
docker run -it \
           --rm \
	       -v /etc/localtime:/etc/localtime:ro \
           --name routing_initial_solution \
           -v ${PWD}:/work \
           -w /work \
           jmarca/initial_solution bash
```

This will create a container and link the current working directory
(`${PWD}`) to the `/work` directory inside of the container.  From
within the container, you can then run all the commands you would
expect from the bash command line prompt.

If you want to run code in the container but *not* spawn a bash
prompt, you can do something like this, assuming you have code in
`src` and data in `data` directories:


```
docker run -it \
           --rm \
	       -v /etc/localtime:/etc/localtime:ro \
           --name routing_initial_solution \
           -v ${PWD}:/work \
           -w /work \
           jmarca/initial_solution python src/run.py -i data/input.csv -o solution.csv
```

# Non-Docker setup

If you do not have Docker, then you can install all of the
dependencies globally using pip.

```
sudo python -m pip install -U ortools
```

Or install locally for just your user:

```
python -m pip install -U --user ortools
```

For non-linux platforms, the approach is the same.  See
https://developers.google.com/optimization/install/python/ for
details.  For example, on windows assuming you have python 3.7
installed, from a command line prompt you can run:

```
python -m pip install --user ortools
```

Just guessing here, but if you're running conda, you'll need to
install pip first.  See https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-pkgs.html?highlight=pip#installing-non-conda-packages

For example, something like (untested)
```
conda install pip
pip install ortools
```

# Run solver

## dependent_breaks branch

To run on the dependent breaks branch, try:

```
python src/run_solver.py -m test/data/matrix.csv --speed 65 -d test/data/demand.csv -t 1 -v 2 --maxtime 16000 --expand 1 --maxlinktime 600
```

## master branch

The solver right now is still in initial stages.  All command line
options are parsed using argparse, and should have help messages.

My typical command line while testing is

```
python src/read_test.py -m data/distance_matrix.csv --speed 60 -d data/demand.csv
```

At the moment, the output is rather underwhelming, as it just tells
you the overall cost of the solution (travel time).

If you run with realistic speeds, some trips are dropped.  Without any
diagnostics on the output implemented yet, my guess is that the truck
cannot get to the origin in time before the time window ends, OR
cannot return to the depot from the destination before the time
horizon expires.

Note that this is without the proper break rules in place.  Things
will get worse when that happens.

Most likely will need to either expand the number of depots, or else
expand the maximum time horizon.

The test coded up in `test/test_output.py` uses a time horizon of
20,000 minutes, or about two weeks, and all trips are served.
Previously I tried 10,000 and one trip got dropped, using a speed of
60mph.

So a longer time horizon should do the trick if trips are being
dropped.



# Tests

Tests are run with pytest.

```
~$ pytest --cov=src
========================= test session starts ========================
platform linux -- Python 3.7.3, pytest-4.4.1, py-1.8.0, pluggy-0.9.0
rootdir: /work, inifile: setup.cfg
plugins: cov-2.6.1
collected 7 items

test/test_demand.py .                                           [ 14%]
test/test_evaluators.py .                                       [ 28%]
test/test_output.py .                                           [ 42%]
test/test_read_csv.py ...                                       [ 85%]
test/test_vehicles.py .                                         [100%]

----------- coverage: platform linux, python 3.7.3-final-0 -----------
Name                     Stmts   Miss  Cover
--------------------------------------------
src/demand.py               28      0   100%
src/evaluators.py           57      0   100%
src/read_csv.py             11      0   100%
src/read_test.py            77     66    14%
src/solution_output.py      62      4    94%
src/vehicles.py             11      0   100%
--------------------------------------------
TOTAL                      246     70    72%


======================== 7 passed in 0.87 seconds ====================
```

The coverage of `solution_output.py` is missing the bits on break output,
because the code doesn't yet have breaks implemented.  The coverage of
`read_test.py` is low because it isn't being tested yet.  (Actually, I
mostly copied its guts into the test for solution output.)
