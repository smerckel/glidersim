import sys

sys.path.insert(0, '..')

import glidersim
import glidersim.configuration
import glidersim.environments


#####################################################################################################
#
# Glider model and gliderflight configuration
#
#####################################################################################################


glider_model = glidersim.glidermodels.Shallow100mGliderModel()

# Set specific parameters for the glider flight model. When supplied, Cd0, mg, and Vg are required.
# The parameter T1..T4 defines the observed pitch as function of the
# buoyancy drive, battery position and pressure (optional), according to
# Estimated pitch relationship:
# tan(pitch) = T1 * buoyancy(m^3) + T2 * battpos(m) + T3 (tan(pitch0)) + T4 P (kbar)
# The values for T1..T4 stem from fitting glider data.
# T1 : 2013.0317025316328
# T2 : -24.259794005453706
# T3 : 0.25292807019452335
# T4 : 0
#glider_model.initialise_gliderflightmodel(Cd0=0.17, mg=73.3, Vg=71.556e-3, T1=2013, T2=-24.5, T3=0.253)
glider_model.initialise_gliderflightmodel(Cd0=0.20, mg=73.3, Vg=71.542e-3, T1=2052, T2=-35.5, T3=0.36) 


#####################################################################################################
#
# Configuration and definition of the environment
#
#####################################################################################################


# Set class variables telling what variable names to use in the bathymery file. Depths are interpreted as positive numbers,
# so, if, as usual, they are written in the NC file as negative, the ELEVATION_FACTOR should be changed accordingly.
glidersim.environments.GliderData.NC_ELEVATION_NAME='bathymetry'
glidersim.environments.GliderData.NC_ELEVATION_FACTOR=1
glidersim.environments.GliderData.NC_LAT_NAME='latc'
glidersim.environments.GliderData.NC_LON_NAME='lonc'

# Normally not required, but this forces dbdreader to read cac files
# from a specific directory. In this case from a directory that is
# included with the source.
glidersim.environments.GliderData.DBDREADER_CACHEDIR = '../data/cac'

if 1:
    # More realistic but takes some time to download current data.
    environment_model = glidersim.environments.DriftModel("comet", download_time=24,
                                                          gliders_directory='../data', bathymetry_filename='../data/bathymetry.nc')
else:
    # Just for testing. Current estimates are inaccurate.
    environment_model = glidersim.environments.GliderData("comet",
                                                          gliders_directory='../data',
                                                          bathymetry_filename='../data/bathymetry.nc')

#####################################################################################################
#
# Simulation configuration
#
#####################################################################################################

# A dictionary with general information on the simulation.
conf = glidersim.configuration.Config('spiral.mi',
                                      description="test",
                                      datestr='20190809',
                                      timestr='15:20',
                                      lat_ini=5440.1099,
                                      lon_ini=646.5619,
                                      mission_directory='../data/comet/spiral',
                                      output='comet-nsb3-spiral.nc',
                                      sensor_settings= dict(),
                                      special_settings={'glider.gps.acquiretime':100.,
                                                        'mission_initialisation_time':400,
                                                        'mission_start':'initial'})

#####################################################################################################
#
# Run the simulation
#
#####################################################################################################


GM=glidersim.glidersim.GliderMission(conf,verbose=False,
                                     glider_model=glider_model,
                                     environment_model = environment_model)
GM.loadmission(verbose=False)
GM.run(dt=0.5,CPUcycle=4,maxSimulationTime=1, end_on_surfacing=True)

# Save the data.
GM.save()

# Run a second simulation, with a normal transect-going glider.

environment_model.reset() # Forces data to be reloaded.

conf = glidersim.configuration.Config('nsb3.mi',
                                      description="test",
                                      datestr='20190821',
                                      timestr='13:54',
                                      lat_ini=5418.9674,
                                      lon_ini=724.5902,
                                      mission_directory='../data/comet/nsb3',
                                      output='comet-nsb3-nsb3.nc',
                                      sensor_settings= dict(c_wpt_lat=5418.000,
                                                            c_wpt_lon= 725.800,
                                                            m_water_vx=0.365,
                                                            m_water_vy=-0.099),
                                      special_settings={'glider.gps.acquiretime':100.,
                                                        'mission_initialisation_time':400},
                                      mission_start="pickup")

# Levels of verbosity:
#
# as option to GliderMission: when True, state changes and actions by the behaviours are displayed.
#
# as option to loadmission(): when True, the parsed mission file is echoed.
#
# as option to run()        : when True, the simulation progress is displayed.


GM=glidersim.glidersim.GliderMission(conf,verbose=False,
                                     glider_model=glider_model,
                                     environment_model = environment_model)
GM.loadmission(verbose=True) # verbose==True -> shows mission description
GM.run(dt=0.5,CPUcycle=4,maxSimulationTime=7/24, end_on_surfacing=False, verbose=True)

GM.save()
