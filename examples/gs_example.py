import sys

sys.path.insert(0, '..')

import glidersim
import glidersim.configuration
import glidersim.environments


glidersim.behaviors.VERBOSE=False

conf = glidersim.configuration.Config('biscay.mi',
                                      description="test",
                                      datestr='20190621',
                                      timestr='07:30',
                                      lat_ini=5432.496,
                                      lon_ini=725.716,
                                      mission_directory='experiment',
                                      output='noname.pck',
                                      sensor_settings= dict(u_use_current_correction=0),
                                      special_settings={'glider.gps.acquiretime':100.},
                                      Cd0=0.14,
                                      mg=60,
                                      Vg=60/1025)

glider_model = glidersim.glidermodels.ShallowGliderModel
environment_model = glidersim.environments.DriftModel()

GM=glidersim.glidersim.GliderMission(conf,interactive=False,glidermodel=glider_model,
                                     environment_model = environment_model)
# set overall glider mass to 51.65 kg (was 51.80)
#GM.glider.m= 51.65 - GM.glider.mb
GM.loadmission(verbose=True)
#GM.run(mission_start='initial', dt=0.5,CPUcycle=4,maxSimulationTime=0.1)
# if mission_start == 'pickup', then c_wpt_lat and c_wpt_lon are looked up from the sensor_Settings.

GM.run(dt=0.5,CPUcycle=4,maxSimulationTime=0.1)

#GM.save()
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
