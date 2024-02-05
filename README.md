<img src="https://github.com/orsoromeo/jet-leg/blob/master/figs/feasible_region.png" alt="hyqgreen" width="400"/>  <img src="https://github.com/orsoromeo/jet-leg/blob/master/figs/four_stance.png" alt="planning" width="400"/>
<img src="https://github.com/orsoromeo/jet-leg/blob/master/figs/force_polygons.png" alt="hyqgreen" width="400"/>  <img src="https://github.com/orsoromeo/jet-leg/blob/master/figs/foothold_planning.png" alt="planning" width="400"/>


# Improved Feasible Region
This python library contains the code used for the computation of the feasibilty criteria in [preprint](https://arxiv.org/abs/2011.07967). In here you can also find the code used to generate the figures and plots of the manuscript. 

<img src="https://github.com/orsoromeo/jet-leg/blob/master/figs/3contacts_F%26A.png" alt="hyqgreen" width="200"/>  <img src="https://github.com/orsoromeo/jet-leg/blob/master/figs/3contacts_onlyA.png" alt="planning" width="200"/>  <img src="https://github.com/orsoromeo/jet-leg/blob/master/figs/4contacts_F%26A.png" alt="hyqgreen" width="200"/>  <img src="https://github.com/orsoromeo/jet-leg/blob/master/figs/4contacts_onlyA.png" alt="planning" width="200"/>

## What you can do with Jet-leg:
- compute the Support region of legged robots as in [Bretl. et al. 2008](https://ieeexplore.ieee.org/abstract/document/4598894); 
- compute the Feasible region of legged robots as in [Orsolino. et al. 2019](https://arxiv.org/abs/1903.07999#) with the incorportation of the robot inertial effects as in [Abdalla. et al. 2023](https://arxiv.org/abs/2011.07967);
- compute the Reachable region as in [Abdalla. et al. 2023](https://arxiv.org/abs/2011.07967);
- compute force polytopes of legged robots given their URDF;
- compare different leg designs and understand their consequences on the robot's balancing capabilities; 
- test various formulations of linear, convex or nonlinear trajectory optimization problems;


## Dependencies

- Numpy
- PyYAML
- Shapely
- Pycddlib
- Scipy
- CVXOPT
- Matplotlib
- Pathos (multiprocessing)

The above dependencies can be installed for Python 3.5 with the following commands:
```
pip install --user numpy
pip install --user pyyaml
pip install --user shapely
pip install --user pycddlib
pip install --user scipy
pip install --user cvxopt==1.2.5
pip install --user matplotlib
pip install --user pathos==0.2.7
```

You can remove all ``--user`` arguments to install these Python modules system-wide.

Other dependencies:
- [Pinocchio](https://github.com/stack-of-tasks/pinocchio) 
- [Pypoman](https://github.com/stephane-caron/pypoman) for the manipulation of polyhedrical object

after cloning remember to do in the jetleg folder:
```
git submodule update --init --recursive
```

## Optional dependencies:

- [rospkg]
```
pip install rospkg
```
- [Ipopt](https://projects.coin-or.org/Ipopt) and its Python interface [Pypi](https://pypi.org/project/ipopt/) for the solution of large-scale nonlinear optimization problems
- [ffmpeg](https://www.ffmpeg.org/) for the generation of Matplotlib animations
```
sudo apt-get install ffmpeg
```
- [unittest](https://docs.python.org/3/library/unittest.html) for testing of dependencies installation and for development


<!--## Installation (no longer used)

Finally, clone this repository and run its setup script:
```
git clone git@gitlab.advr.iit.it:rorsolino/jet-leg.git
cd jet-leg
python setup.py build
python setup.py install --user
```
-->

## Testing the library
After completing the installation navigate to the [examples](https://gitlab.advr.iit.it/rorsolino/jet-leg/tree/master/examples) folder:

- [single_iterative_projection_example.py](https://github.com/orsoromeo/jet-leg/blob/master/examples/iterative_projection/single_iterative_projection_example.py) can be used to see how to set up an iterative projection problem in order to compute the friction/actuation/feasible region;
- [check_stability_lp_example.py](https://github.com/orsoromeo/jet-leg/blob/master/examples/static_equilibrium_check/check_stability_lp_example.py) can be used to quickly check whether the given robot configuration is statically stable or not (without explicitly computing the feasible region);
- [plotIPstatistics.py](https://github.com/orsoromeo/jet-leg/blob/master/examples/figures_code/plotIPstatistics.py) can be used to generate some statistics about the computation time of the IP algorithm for random feet positions (see Fig. 6 of the [preprint](https://arxiv.org/abs/1903.07999#));
- [plotInstantaneousActuationRegionVariableMass.py](https://github.com/orsoromeo/jet-leg/blob/master/examples/figures_code/plotInstantaneousActuationRegionVariableMass.py) can be used to generate a plot that shows how the feasible regions can changes depending on the gravitational force acting on the robot's center of mass (see Fig. 8 of the [preprint](https://arxiv.org/abs/1903.07999#)) 

## Troubleshooting

- if CVXOPT is not found even after trying the pip-installation, we then suggest to try install the version 1.1.4 of CVXOPT using Synaptic or to clone and install it manually after building.
- IMPORTANTE NOTE: delete every previous installation of cvxopt that is in the system using locate cvxopt (after sudo updatedb)

## See also

- The [pypoman](https://github.com/stephane-caron/pypoman) and [pymanoid](https://github.com/stephane-caron/pymanoid) libraries developed by Stéphane Caron
- Komei Fukuda's [Frequently Asked Questions in Polyhedral Computation](http://www.cs.mcgill.ca/~fukuda/soft/polyfaq/polyfaq.html)
- The
  [Polyhedron](http://doc.sagemath.org/html/en/reference/discrete_geometry/sage/geometry/polyhedron/constructor.html) class in [Sage](http://www.sagemath.org/)
- The [StabiliPy](https://github.com/haudren/stabilipy) package provides a more
  general recursive projection method
