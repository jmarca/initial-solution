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
