# Open Solver Initial Solution

[![Build
Status](https://travis-ci.org/jmarca/initial-solution.svg?branch=master)](https://travis-ci.org/jmarca/initial-solution)
[![Maintainability](https://api.codeclimate.com/v1/badges/944802efa25831f791d8/maintainability)](https://codeclimate.com/github/jmarca/initial-solution/maintainability)
[![Test
Coverage](https://api.codeclimate.com/v1/badges/944802efa25831f791d8/test_coverage)](https://codeclimate.com/github/jmarca/initial-solution/test_coverage)

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

## master branch

There are two executables that can be run: `src/run_initial_routes.py`
and `src/run_without_constraints.py`.


```
python src/run_initial_routes.py -h
usage: run_initial_routes.py [-h] [-m,--matrixfile MATRIXFILE]
                             [-d,--demandfile DEMAND]
                             [-o,--vehicleoutput VEHICLE_OUTPUT]
                             [--demandoutput DEMAND_OUTPUT]
                             [--summaryoutput SUMMARY_OUTPUT] [--speed SPEED]
                             [--maxtime HORIZON] [-v,--vehicles NUMVEHICLES]
                             [--pickup_time PICKUP_TIME]
                             [--dropoff_time DROPOFF_TIME]
                             [-t, --timelimit TIMELIMIT]
                             [--narrow_destination_timewindows DESTINATION_TIME_WINDOWS]
                             [--drive_dim_start_value DRIVE_DIMENSION_START_VALUE]
                             [--debug DEBUG]

Solve assignment of truck load routing problem, give hours of service rules
and a specified list of origins and destinations

optional arguments:
  -h, --help            show this help message and exit
  -m,--matrixfile MATRIXFILE
                        CSV file for travel matrix (distances)
  -d,--demandfile DEMAND
                        CSV file for demand pairs (origin, dest, time windows)
  -o,--vehicleoutput VEHICLE_OUTPUT
                        CSV file for dumping output
  --demandoutput DEMAND_OUTPUT
                        CSV file for dumping output for demand details
                        (including invalid demands, etc)
  --summaryoutput SUMMARY_OUTPUT
                        A file for dumping the human-readable summary output
                        for the assignment
  --speed SPEED         Average speed, miles per hour. Default is 55 (miles
                        per hour). Distance unit should match that of the
                        matrix of distances. The time part should be per hours
  --maxtime HORIZON     Max time in minutes. Default is 10080 minutes, which
                        is 7 days.
  -v,--vehicles NUMVEHICLES
                        Number of vehicles to create. Default is 100.
  --pickup_time PICKUP_TIME
                        Pick up time in minutes. Default is 15 minutes.
  --dropoff_time DROPOFF_TIME
                        Drop off time in minutes. Default is 15 minutes.
  -t, --timelimit TIMELIMIT
                        Maximum run time for solver, in minutes. Default is 5
                        minutes.
  --narrow_destination_timewindows DESTINATION_TIME_WINDOWS
                        If true, limit destination node time windows based on
                        travel time from corresponding origin. If false,
                        destination nodes time windows are 0 to args.horizon.
                        Default true (limit the time window).
  --drive_dim_start_value DRIVE_DIMENSION_START_VALUE
                        Due to internal solver mechanics, the drive dimension
                        can't go below zero (it gets truncated at zero). So to
                        get around this, the starting point for the drive time
                        dimension has to be greater than zero. The default is
                        1000. Change it with this variable
  --debug DEBUG         Turn on some print statements.
```

The `run_without_constraints.py` options are similar.  The main
difference between the two is that `run_without_constraints.py` will
solve the assignment problem without including any breaks at all.  The
below text refers to the `run_initial_routes.py` program, but aside
from break-specific aspects, the same comments apply to the without
constraints program.

Many of these options tweak things that influence the travel times,
such as the speed and the pickup and drop off times.  Others are
related to the internals of the solver
(`--narrow_destination_timewindows` and `--drive_dim_start_value`) and
probably should not be changed.

A typical solver run allowing the solver 10 minutes to think is as follows:

```
 python src/run_initial_routes.py -m data/distance_matrix.csv --speed 65 -d data/demand.csv -t 10 -v 75  --maxtime 20000  --summaryoutput out.txt
```

In this case only 75 vehicles are used, because many of the trips are
difficult to serve with a speed of 65mph, because the arrival time at
the pickup node is *after* the closing of the pickup time window.

The human-readable output in this case is also very long, and will
probably scroll past the screen.  In that case, you can pass a file to
"--summaryoutput", as was done here.

The program will always dump two csv files.  The first is a per
vehicle file that shows the vehicle usage.  For example:

```
demand,distance,location,order,time,veh
0,0,0,0,2107,0
0,357,-1,1,2437,0
0,357,-1,2,2797,0
0,357,-1,3,3727,0
0,357,-1,4,4087,0
1,187,29,5,4860,0
0,357,-1,6,5205,0
0,357,-1,7,5565,0
0,357,-1,8,6495,0
0,357,-1,9,6855,0
0,164,-1,10,7607,0
0,165,-1,11,7790,0
-1,331,33,12,8696,0
0,357,-1,13,9041,0
0,357,-1,14,9401,0
0,357,-1,15,10331,0
0,357,-1,16,10691,0
0,194,0,17,11471,0
```

The second is a file showing the output from the perspective of the
demand items.  For example:

```
dropoff_distance,dropoff_node,dropoff_order,dropoff_time,pickup_distance,pickup_node,pickup_order,pickup_time,veh
331,33,12,8696,187,29,5,4860,0
```

The names of these files default to `demand_output{_N}.csv` and
`vehicle_output{_N}.csv`.  If there are collisions with previously
written files, the N part will be incremented by one.






# Tests

The tests are woefully out of date.  When they weren't out of date,
coverage was pretty good, but at this point the tests most likely
won't even run properly.

Tests are run with pytest.

```
pytest --cov=src
==================== test session starts ============================
platform linux -- Python 3.7.3, pytest-4.5.0, py-1.8.0, pluggy-0.11.0
rootdir: /work, inifile: setup.cfg
plugins: cov-2.7.1
collected 13 items

test/test_breaks.py ......                                     [ 46%]
test/test_demand.py .                                          [ 53%]
test/test_evaluators.py .                                      [ 61%]
test/test_output.py .                                          [ 69%]
test/test_read_csv.py ...                                      [ 92%]
test/test_vehicles.py .                                        [100%]

----------- coverage: platform linux, python 3.7.3-final-0 -----------
Name                             Stmts   Miss  Cover
----------------------------------------------------
src/break_node.py                   18      2    89%
src/breaks.py                      120      5    96%
src/demand.py                      260     35    87%
src/evaluators.py                  192     79    59%
src/initial_routes.py              205     90    56%
src/model_run.py                   191     34    82%
src/read_csv.py                     11      0   100%
src/run_initial_routes.py           60     44    27%
src/run_without_constraints.py      62     46    26%
src/solution_output.py             303    165    46%
src/vehicles.py                     11      0   100%
----------------------------------------------------
TOTAL                             1433    500    65%

=================== 13 passed in 22.88 seconds =======================
```

The coverage isn't great, but at least they're passing.
