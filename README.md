# glidersim

## Introduction

Glidersim is an attempt to simulate the behaviour of (typically
Slocum) ocean gliders. The key reason for developing this software is
that for some glider operations, notably in German waters, it is
compulsary to provide trajectory forecasts of each deployed glider
with a time horizon of 12 hours. Based on these forecasts, regions of
bounding boxes are defined, spanning the forecasted tracks. This
information is sent to coastal ship traffic control centres, who issue
warnings to ships informing them regarding the ongoing scientific
experiments.

In order to run these simulations, the software implements

- a simulator of the glider's software, so that given the same mission
  file active on a glider, the behaviour of the simulator is similar
  to that of the real glider;
- a simulator of the glider's actuators (buoyancy pump, pitch battery motor, and fin);
- a simulator of the glider's dynamics;
- a digital environment for the glider to fly in.

The first two simulators are primarily coded in this python package. The glider dynamics are based on the python [gliderflight](https://github/smerckel/gliderflight) package, which is based on the published paper *A dynamic flight model
for Slocum gliders and implications for turbulence microstructure
measurements* [1].

The digital environment plays a major role in how the glider actually
moves, and provides the input to the glider flight model. Each
environment class implements a method that return for a given time and
(latitude, longitude, depth) coordinate the in-situ density, water
depth, surface elevation and a three-dimensional current vector.

For the source of digital environments a few options are
available. For the purpose described above, environmental data are
obtained from the most recent data files sent back by the glider,
supplemented by a bathymetry data file of the region. The currents are
represented by an estimate (by the glider) of depth-averged currents,
averaged in time over a subsurface period. In particular for tidal
regions this is not so accurate. An improved method to obtain currents
from glider observations uses a Kalman filter [2]. Other sources of
input can be model output. The python code provides ways for the GETM
model, which uses curvilinear sigma grids and netCDF files for output.

## Installation

The source code of glidersim can be downloaded from
[github](https://github.com/smerckel/glidersim). Most dependencies can
be taken care of by running 'pip install -r requirements.txt', but
some python packages are not available via pypi and need to be
downloaded from github and installed manually. This applies to the packages [latlon](https://github.com/smerckel/latlon) and [GliderNetCDF](https://github.com/smerckel/GliderNetCDF). The following bash script can be used to install all required pakcages.

```
#!/bin/bash

# get the source of additional packages from github
git clone https://github.com/smerckel/latlon.git
git clone https://github.com/smerckel/GliderNetCDF.git
pip install ./latlon ./GliderNetCDF

# Get and install glidersim.
git clone https://github.com/smerckel/glidersim.git
pip install glidersim
```

## Example

An example of how this software can be used is given by the script
`gs_example.py`, which is to be run from the subdirectory
`examples`. This script simulates two different missions carried out
with the glider * Comet* in the North Sea in August 2019. The
corresponding data files can be found in the subdirectory `data`, see
the tree below.

```
glidersim
├── data
│   ├── cac               <- cache files required to read glider binary data files
│   └── comet
│       ├── from-glider   <- glider binary data files 
│       ├── nsb3          <- directory with mission files for nsb3 mission
│       │   ├── mafiles   <- all required ma files, as they were on the glider 
│       │   └── missions  <- the nsb3.mi mission file                          
│       └── spiral        <- directory with mission files for nsb3 mission     
│           ├── mafiles   <- all required ma files, as they were on the glider 
│           ├── missions  <- the spiral.mi mission file                          
│           └── trim      <- glider binary data used to calibrate the glider flight model.
├── examples
└── glidersim
```

Below is an example script, adapted from `gs_example.py` shipped with this software.
```
import glidersim
import glidersim.configuration
import glidersim.environments

# Define a glider model. In this case a Slocum shallow 100 m.
glider_model = glidersim.glidermodels.Shallow100mGliderModel()

# Set the glider flight parameters.
glider_model.initialise_gliderflightmodel(Cd0=0.20, mg=73.3, Vg=71.542e-3, T1=2052, T2=-35.5, T3=0.36) 

# The bathymetry is read from a netcdf file. Set the names of the fields that nead to be read.
glidersim.environments.GliderData.NC_ELEVATION_NAME='bathymetry'
glidersim.environments.GliderData.NC_ELEVATION_FACTOR=1
glidersim.environments.GliderData.NC_LAT_NAME='latc'
glidersim.environments.GliderData.NC_LON_NAME='lonc'

# Tell dbdreader where to get the cache files from
glidersim.environments.GliderData.DBDREADER_CACHEDIR = '../data/cac'

# Use current estimates from the BSH model, accessible via an online API:
environment_model = glidersim.environments.DriftModel("comet", download_time=24,
		                                      gliders_directory='../data',
						      bathymetry_filename='../data/bathymetry.nc')
# Create a configuarion dictionary
conf = glidersim.configuration.Config('nsb3.mi',                # the mission name to run
                                      description="test",       # descriptive text used in the output file
                                      datestr='20190821',       # start date of simulation
                                      timestr='13:54',          # and time      
                                      lat_ini=5418.9674,        # starting latitude
                                      lon_ini=724.5902,         # starting longitude
                                      mission_directory='../data/comet/nsb3',  # where the missions and mafiles directories are found
                                      output='comet-nsb3-nsb3.nc',             # name of output file (pickled files (.pck) can also be used
                                      sensor_settings= dict(c_wpt_lat=5418.000,# set some glider parameters
                                                            c_wpt_lon= 725.800,
                                                            m_water_vx=0.365,
                                                            m_water_vy=-0.099),
                                      special_settings={'glider.gps.acquiretime':100., # how long the GPS should take to get a reading
                                                        'mission_initialisation_time':400}, # how much time the glider needs to initialise.
                                      mission_start="pickup")    # if not set, a new mission is assumed, otherwise it is a continuation of
				                                 # a previous dive.

# Create a GliderMission object, specifying the glider hardware and environment.
GM=glidersim.glidersim.GliderMission(conf,verbose=False,
                                     glider_model=glider_model,
                                     environment_model = environment_model)
# load the mission and show the contents.				     
GM.loadmission(verbose=True)

# Run the simulation with 0.5 seconds time step. The glider CPU cycle
# is set to 4 seconds. We simulate only 7 hours, and show some
# diagnostic output.
GM.run(dt=0.5,CPUcycle=4,maxSimulationTime=7/24, end_on_surfacing=False, verbose=True)

# Save the results in a file for later analysis
GM.save()
```

## Output

The output is written to a netCDF file (default) or to pickled
files. The netCDF file contains a long list of variables. Most of them
start either with c_ m_ u_ or x_ and are equivalent in meaning with
respect to the glider parameters. Some other parameters are added for
diagnosis.

For example, the glider depth is represented by the variable
`m_depth`, and can be plotted as function of time (in seconds since
1970) using the variable `m_present_time`, which is in the netCFD file
equal to the time dimension. The script `examples/validate_model.py`
compares the output generated with the glidersim model with the actual
glider data files for the two simulated missions.

## Disclaimer

The glidersim software is not a one-to-one implementation of the
actual glider software. The actual glider source code is not only
rather complex, but also closed source. The glidersim code implements
only the essential bits of the glider software, required for
simulating normal operation. The implementation is on the basis of how
I *think* the glider software is programmed, or how I think the glider
behaves (from experience). This software comes *as is*, see also the
GPLv3 license.


Lucas Merckelbach

## References
[1] Merckelbach, L., A. Berger, G. Krahmann, M. Dengler, and J. Carpenter, 2019: A
   dynamic flight model for Slocum gliders and implications for
   turbulence microstructure measurements. J. Atmos. Oceanic
   Technol. 36(2), 281-296, doi:10.1175/JTECH-D-18-0168.1

[2] Merckelbach, L.: 2016 Depth-averaged instantaneous currents in a tidally dominated shelf sea from glider observations Biogeosciences 13(24):6637-6649 DOI: 10.5194/bg-13-6637-2016