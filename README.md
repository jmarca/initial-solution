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


## feature/initial_routes branch

Works for 100 trips case.

Command line is:

```
python src/run_solver.py -m data/distance_matrix.csv --speed 65 -d data/demand.csv -t 5 -v 90  --maxtime 15000 --breaks_at_nodes 1
```
Running time is

```
real	15m29.336s
user	12m23.496s
sys	3m6.715s
```

## feature/breaks_at_nodes branch

This branch allows for breaks at nodes, as breaks using the breaks
functionality is broken.

To run this, do something like:

```
python src/run_solver.py -m data/distance_matrix.csv --speed 65 -d test/data/demand3.csv -t 1 -v 5  --maxtime 15000 --breaks_at_nodes 1
```

Output looks like:

```
Objective: 2008012111
Breaks:
Routes:
Route for vehicle 0:
node 0, mapnode 0, Load 0, Drive Time 16:40:00,  Time(0:00:00,2 days, 23:38:00) Slack(0:00:00,2 days, 23:38:00) Time(0:00:00)  Link (Time 0:00:00, distance 0 mi), visits: 0
 ->node 12, mapnode -1, Load 0, Drive Time 11:13:00,  Time(5:33:00,3 days, 5:11:00) Slack(0:00:00,2 days, 23:38:00) Time(5:33:00)  Link (Time 5:33:00, distance 360 mi), visits: 1
 ->node 2, mapnode 8, Load 0, Drive Time 17:54:00,  Time(3 days, 9:00:00,3 days, 20:45:00) Slack(0:00:00,11:45:00) Time(15:34:00)  Link (Time 5:34:00, distance 361 mi), visits: 2
 ->node 14, mapnode -1, Load 1, Drive Time 1 day, 7:06:00,  Time(3 days, 16:47:00,4 days, 4:32:00) Slack(0:00:00,11:45:00) Time(7:47:00)  Link (Time 7:32:00, distance 489 mi), visits: 3
 ->node 15, mapnode -1, Load 1, Drive Time 23:52:00,  Time(4 days, 6:33:00,4 days, 18:18:00) Slack(0:00:00,11:45:00) Time(13:46:00)  Link (Time 3:46:00, distance 244 mi), visits: 4
 ->node 6, mapnode 51, Load 1, Drive Time 1 day, 3:39:00,  Time(4 days, 20:20:00,5 days, 8:05:00) Slack(0:00:00,4 days, 23:25:00) Time(13:47:00)  Link (Time 3:47:00, distance 245 mi), visits: 5
 ->node 16, mapnode -1, Load 0, Drive Time 18:39:00,  Time(4 days, 22:35:00,9 days, 22:00:00) Slack(0:00:00,4 days, 23:25:00) Time(2:15:00)  Link (Time 2:00:00, distance 130 mi), visits: 6
 -> 0 Load(0)  Time(5 days, 10:35:00,10 days, 10:00:00)  Link time(12:00:00) Link distance(130 mi), visits 7
Distance of the route: 1959 miles
Loads served by route: 1
Time of the route: 5 days, 10:35:00

Route for vehicle 1:
node 0, mapnode 0, Load 0, Drive Time 16:40:00,  Time(0:00:00,1 day, 6:28:00) Slack(0:00:00,1 day, 6:28:00) Time(0:00:00)  Link (Time 0:00:00, distance 0 mi), visits: 0
 ->node 17, mapnode -1, Load 0, Drive Time 1 day, 5:30:00,  Time(9:08:00,1 day, 15:36:00) Slack(0:00:00,1 day, 6:28:00) Time(9:08:00)  Link (Time 9:08:00, distance 593 mi), visits: 1
 ->node 18, mapnode -1, Load 0, Drive Time 23:04:00,  Time(23:42:00,2 days, 6:10:00) Slack(0:00:00,1 day, 6:28:00) Time(14:34:00)  Link (Time 4:34:00, distance 296 mi), visits: 2
 ->node 3, mapnode 39, Load 0, Drive Time 1 day, 3:39:00,  Time(2 days, 9:00:00,2 days, 20:45:00) Slack(0:00:00,11:45:00) Time(14:35:00)  Link (Time 4:35:00, distance 297 mi), visits: 3
 ->node 19, mapnode -1, Load 1, Drive Time 18:20:00,  Time(2 days, 10:56:00,2 days, 22:41:00) Slack(0:00:00,11:45:00) Time(1:56:00)  Link (Time 1:41:00, distance 109 mi), visits: 4
 ->node 7, mapnode 60, Load 1, Drive Time 20:02:00,  Time(2 days, 22:38:00,3 days, 10:23:00) Slack(0:00:00,5 days, 17:56:00) Time(11:42:00)  Link (Time 1:42:00, distance 110 mi), visits: 5
 ->node 20, mapnode -1, Load 0, Drive Time 1 day, 4:04:00,  Time(3 days, 9:28:00,9 days, 3:24:00) Slack(0:00:00,5 days, 17:56:00) Time(10:50:00)  Link (Time 10:35:00, distance 687 mi), visits: 6
 ->node 21, mapnode -1, Load 0, Drive Time 22:22:00,  Time(4 days, 0:46:00,9 days, 18:42:00) Slack(0:00:00,5 days, 17:56:00) Time(15:18:00)  Link (Time 5:18:00, distance 344 mi), visits: 7
 -> 0 Load(0)  Time(4 days, 16:04:00,10 days, 10:00:00)  Link time(15:18:00) Link distance(344 mi), visits 8
Distance of the route: 2780 miles
Loads served by route: 1
Time of the route: 4 days, 16:04:00

Route for vehicle 2:
node 0, mapnode 0, Load 0, Drive Time 16:40:00,  Time(0:00:00,1 day, 17:02:00) Slack(0:00:00,1 day, 17:02:00) Time(0:00:00)  Link (Time 0:00:00, distance 0 mi), visits: 0
 ->node 1, mapnode 16, Load 0, Drive Time 20:23:00,  Time(1 day, 9:00:00,1 day, 20:45:00) Slack(0:00:00,11:45:00) Time(3:43:00)  Link (Time 3:43:00, distance 242 mi), visits: 1
 ->node 10, mapnode -1, Load 1, Drive Time 13:34:00,  Time(1 day, 13:26:00,2 days, 1:11:00) Slack(0:00:00,11:45:00) Time(4:26:00)  Link (Time 4:11:00, distance 271 mi), visits: 2
 ->node 5, mapnode 20, Load 1, Drive Time 22:28:00,  Time(2 days, 3:38:00,2 days, 15:23:00) Slack(0:00:00,7 days, 14:55:00) Time(14:12:00)  Link (Time 4:12:00, distance 273 mi), visits: 3
 ->node 11, mapnode -1, Load 0, Drive Time 14:04:00,  Time(2 days, 6:29:00,9 days, 21:24:00) Slack(0:00:00,7 days, 14:55:00) Time(2:51:00)  Link (Time 2:36:00, distance 169 mi), visits: 4
 -> 0 Load(0)  Time(2 days, 19:05:00,10 days, 10:00:00)  Link time(12:36:00) Link distance(169 mi), visits 5
Distance of the route: 1124 miles
Loads served by route: 1
Time of the route: 2 days, 19:05:00

Route for vehicle 3:
node 0, mapnode 0, Load 0, Drive Time 16:40:00,  Time(0:00:00,10 days, 10:00:00) Slack(0:00:00,10 days, 10:00:00) Time(0:00:00)  Link (Time 0:00:00, distance 0 mi), visits: 0
 -> 0 Load(0)  Time(0:00:00,10 days, 10:00:00)  Link time(0:00:00) Link distance(0 mi), visits 1
Distance of the route: 0 miles
Loads served by route: 0
Time of the route: 0:00:00

Route for vehicle 4:
node 0, mapnode 0, Load 0, Drive Time 16:40:00,  Time(0:00:00,10 days, 10:00:00) Slack(0:00:00,10 days, 10:00:00) Time(0:00:00)  Link (Time 0:00:00, distance 0 mi), visits: 0
 -> 0 Load(0)  Time(0:00:00,10 days, 10:00:00)  Link time(0:00:00) Link distance(0 mi), visits 1
Distance of the route: 0 miles
Loads served by route: 0
Time of the route: 0:00:00

Total Distance of all routes: 5863 miles
Total Loads picked up by all routes: 3
Total Time of all routes: 12 days, 21:44:00
```

Dummy nodes are indicated by "mapnode -1."

Disjunction penalties on nodes and dummy nodes are different, so that
you can read the Objective value and see what is happening.  Node
penalties are set to 1000000000; dummy node penalties are set to
1000000.

For example, the above value of
```
Objective: 2008012111
```

The left most 2xxx tells me that two nodes are dropped---one trip
pair.

The inner 0080... tells me that 8 of the dummy nodes are dropped.  I
don't care about these as they only exist to implement nodes.

The final 12111 value is the actual cost of travel incurred by the
vehicles serving demand.

A pending todo item is to add the list of dropped demand pairs to the
output.



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
