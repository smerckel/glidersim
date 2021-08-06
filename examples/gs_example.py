import sys

sys.path.insert(0, '..')

import glidersim
import glidersim.configuration
import glidersim.environments


conf = glidersim.configuration.Config('spiral.mi',
                                      description="test",
                                      datestr='20190809',
                                      timestr='15:20',
                                      lat_ini=5440.1099,
                                      lon_ini=646.5619,
                                      mission_directory='../data/comet/nsb3',
                                      output='comet-nsb3.nc',
                                      sensor_settings= dict(u_use_current_correction=0),
                                      special_settings={'glider.gps.acquiretime':100.},
                                      Cd0=0.14,
                                      mg=60,
                                      Vg=60/1025)

glider_model = glidersim.glidermodels.Shallow100mGliderModel

glidersim.environments.GliderData.NC_ELEVATION_NAME='bathymetry'
glidersim.environments.GliderData.NC_ELEVATION_FACTOR=1
glidersim.environments.GliderData.NC_LAT_NAME='latc'
glidersim.environments.GliderData.NC_LON_NAME='lonc'

#environment_model = glidersim.environments.DriftModel("comet", download_time=12,
#                                                      gliders_directory='../data', bathymetry_filename='../data/bathymetry.nc')

environment_model = glidersim.environments.GliderData("comet",
                                                      gliders_directory='../data',
                                                      bathymetry_filename='../data/bathymetry.nc')



GM=glidersim.glidersim.GliderMission(conf,interactive=False,verbose=False,glidermodel=glider_model,
                                     environment_model = environment_model)
# set overall glider mass to 51.65 kg (was 51.80)
#GM.glider.m= 51.65 - GM.glider.mb
GM.loadmission(verbose=False)
#GM.run(mission_start='initial', dt=0.5,CPUcycle=4,maxSimulationTime=0.1)
# if mission_start == 'pickup', then c_wpt_lat and c_wpt_lon are looked up from the sensor_Settings.

GM.run(dt=0.5,CPUcycle=4,maxSimulationTime=1, end_on_surfacing=True)

GM.save()
d=GM.get("m_depth")
pitch = GM.get("m_pitch")
cpitch = GM.get("c_pitch")
battpos = GM.get("m_battpos")
cbattpos = GM.get("c_battpos")
t = GM.get("m_present_time")
w = GM.get("x_upward_glider_velocity")
tm = t -t[0]
x=GM.get("m_lmc_x")
y=GM.get("m_lmc_y")
ballast_pumped = GM.get("m_ballast_pumped") 
heading = GM.get("m_heading")
