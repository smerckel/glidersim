import glidersim
import glidersim.configuration
import glidersim.timeseries
import numpy as np
import ndf
import dbdreader

conf = glidersim.configuration.Config('micro.mi',
                                      description="test",
                                      datestr='20150409',
                                      timestr='15:12',
                                      lat_ini=4259.024,
                                      lon_ini=544.920,
                                      output='noname.pck',
                                      missions='toulon',
                                      mafiles='toulon',
                                      sensorSettings=[('u_use_current_correction',0)],
                                      specialSettings=['glider.gps.acquiretime=1.'],
                                      #directory='/home/lucas/samba/cosyna/netcdf/PO-Flow/gb_1km',
                                      storePeriod=1)
#


class DeepGliderModel(glidersim.glidermodels.DeepDynamics,
                      glidersim.glidermodels.DeepGliderModel,
                      glidersim.timeseries.OneDimEnvironment):

    def __init__(self,datestr,timestr,lat,lon,**kwds):
        if "pitch_model_parameters" in kwds.keys():
            pitch_model_parameters=kwds["pitch_model_parameters"]
        else:
            pitch_model_parameters=(1300,-30,0.)
        glidersim.glidermodels.DeepDynamics.__init__(self,x=0,y=0,
                                                       pitch_model_parameters=pitch_model_parameters)
        glidersim.glidermodels.DeepGliderModel.__init__(self,datestr,timestr,lat,lon)
        print("Glider simulation start coordinates:",datestr,timestr,lat,lon)
        glidersim.timeseries.OneDimEnvironment.__init__(self)


#glidersim.behaviors.VERBOSE=True
GM=glidersim.glidersim.GliderMission(conf,interactive=False,glidermodel=DeepGliderModel)
GM.glider.m= 58.0 - GM.glider.mb                                     
GM.glider.V=56.389e-3
GM.glider.Cd=0.155
GM.glider.epsilon=4.68e-10
GM.glider.set_pitch_model_parameters((1343.52,-19.14,-0.145,1.333))

GM.loadmission(verbose=True)
# Set the data from a 1D profile
density_data=ndf.NDF("toulon/density_profile_toulon.ndf")
density_profile=density_data.get("rho")
GM.glider.set_data(density_profile[0],density_profile[1])


GM.glider.pitchPID.Kp=3 # u_pitch_ap_gain
GM.glider.pitchPID.Ki=0.
GM.glider.pitchPID.Kd=0.
GM.glider.pitchPID.deadband=0.05# radians.


GM.run(dt=1.,ndtCPU=4,maxSimulationTime=0.13,ndtNetCDF=1,end_on_surfacing=1)
#GM.save()
d=GM.get("m_depth")
tm=GM.get("m_present_time")
b=GM.get("m_ballast_pumped")
p=GM.get("m_pitch")
pc=GM.get("c_pitch")
bp=GM.get("m_battpos")
bpc=GM.get("c_battpos")
dbd=dbdreader.MultiDBD(pattern="/home/lucas/gliderdata/toulon_201504/hd/comet-2015-098-03-000.?bd")

md=dbd.get("m_depth")
mb=dbd.get("m_de_oil_vol")
mp=dbd.get("m_pitch")
cbp=dbd.get("c_battpos")
mbp=dbd.get("m_battpos")

import pylab as pl
import publication
publication.setup()
tm-=0
t0=md[0][0]
f,ax=pl.subplots(3,1,sharex=True,figsize=(10,7.3))
ax[0].plot(tm-t0,d,'r',label='simulation')
ax[0].plot(md[0]-t0,md[1],'b',label='data')
ax[1].plot(tm-t0,p,'r',label='simulation')
ax[1].plot(mp[0]-t0,mp[1],'b',label='data')
ax[2].plot(tm-t0,bp,'r',label='simulation')
ax[2].plot(mbp[0]-t0,mbp[1],'b',label='data')
ax[2].plot(tm-t0,bpc,'y',label='simulation commanded')
ax[2].plot(cbp[0]-t0,cbp[1],'g',label='data commanded')
ax[2].set_xlabel(r'time (s)')
ax[0].set_ylabel(r'depth (m)')
ax[1].set_ylabel(r'pitch (rad)')
ax[2].set_ylabel(r'battery pos (in)')
ax[0].set_ylim(800,-5)
ax[0].legend(loc='lower right',fontsize='small')
ax[1].legend(loc='lower right',fontsize='small')
ax[2].legend(loc='upper center', fontsize='small')

pl.show()
#x=GM.get("m_lmc_x")
#y=GM.get("m_lmc_y")



