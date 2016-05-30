import os

import dbdreader
import glidersim
import glidersim.configuration

# setting the name for U and V velocities as used int he getm data files.
glidersim.glidermodels.GetmEnvironment.Uname='eastward_sea_water_velocity'
glidersim.glidermodels.GetmEnvironment.Vname='northward_sea_water_velocity'
glidersim.glidermodels.GetmEnvironment.UseW=False


class SBD(object):
    def __init__(self,sbd_directory="sbd"):
        self.sbd=dbdreader.MultiDBD(pattern=os.path.join(sbd_directory,"*.sbd"))
        self.battpos,self.pitch=self.sbd.get_xy('m_battpos','m_pitch')
    
    def get_timings(self):
        tms=self.sbd.get('m_depth')[0]
        datestr,timestr=glidersim.timeconversion.epochToDateTimeStr(tms[0])
        simulation_time=(tms[-1]-tms[0])/86400.
        return datestr,timestr,simulation_time
                                    
        

conf = glidersim.configuration.Config('helgo.mi',
                                      description="for comparing with real glider data",
                                      datestr='20110212',
                                      timestr='16:06',
                                      lat_ini=5432.496,
                                      lon_ini=725.716,
                                      output='helgo-compare.pck',
                                      sensorSettings=[('u_use_current_correction',0)],
                                      specialSettings=['glider.gps.acquiretime=100.'],
                                      directory='/home/lucas/getm_data/kofserver2',
                                      storePeriod=1,mafiles='calibration',
                                      missions='calibration')


sbd=SBD('calibration')
conf.datestr,conf.timestr,simulation_time=sbd.get_timings()
GM=glidersim.glidersim.GliderMission(conf,interactive=False)
GM.glider.m= 51.55 - GM.glider.mb                                     
GM.glider.cg=(0,-0.006)
GM.LC.pitchPID.Kp=1.0
GM.LC.pitchPID.Ki=0.01
GM.glider.pitchingMoment=4e-3
#
GM.loadmission()
GM.run(dt=1.,ndtCPU=4,maxSimulationTime=simulation_time/20.)
depth=GM.get('m_depth')
tm=GM.get('m_present_time')
pitch=GM.get('m_pitch')
cpitch=GM.get('c_pitch')
battpos=GM.get('m_battpos')
cbattpos=GM.get('c_battpos')
volume=GM.get('m_ballast_pumped')
from pylab import *
plot(depth,label='depth')
plot(battpos,label='battpos')
plot(cbattpos,label='cbattpos')
plot(pitch*10,label='pitch')
plot(cpitch*10,label='cpitch')
legend()
draw()
