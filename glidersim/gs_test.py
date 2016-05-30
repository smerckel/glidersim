import numpy as np
from . import glidersim
from . import configuration
from . import timeconversion
from . import glidermodels

from  scipy.interpolate import interp1d

class my_interp1d(interp1d):
    def __init__(self,x,y):
        interp1d.__init__(self,x,y)

    def __call__(self,x):
        if x<self.x[0]:
            _x=self.x[0]
        elif x>self.x[-1]:
            _x=self.x[-1]
        else:
            _x=x
        return interp1d.__call__(self,_x)

#lidersim.behaviors.VERBOSE=True

glidername='sebastian'
datestr="20130518"
timestr="12:32"
lat=4158.725
lon=1607.011
mission='adria.mi'
conf = configuration.Config(mission,
                            description='Glidersimulator for %s'%(glidername),
                            datestr=datestr,
                            timestr=timestr,
                            lat_ini=lat,
                            lon_ini=lon,
                            output="%s-%s.pck"%(glidername,mission),
                            directory='/home/lucas/working/molcard/coconet/COCONET',
                            storePeriod=10)


class SimpleGliderModel(glidermodels.SimpleDynamics,
                        glidermodels.GliderModel):
    def __init__(self,datestr,timestr,lat,lon,directory,**kwds):
        glidermodels.SimpleDynamics.__init__(self,x=0,y=0)
        glidermodels.GliderModel.__init__(self,datestr,timestr,lat,lon)
        # some preset parameters:
        self.water_depth=350.
        self.Sal=37.
        self.T=20.
        self.SalFun=None
        self.TempFun=None

    def set_salinity_profile(self,z,S):
        self.SalFun=my_interp1d(z,S)

    def set_temperature_profile(self,z,T):
        self.TempFun=my_interp1d(z,T)

    def get_current(self,t,lat,lon,z):
        # returns all zeros for u,v,w,waterdepth,eta,S,T
        S=self.SalFun(z)
        T=self.TempFun(z)
        return 0,0,0,self.water_depth,0,S,T

gm=glidersim.GliderMission(conf,glidermodel=SimpleGliderModel,interactive=False)
gm.datatransfertime=7*60 # 7 minutes
# some glider settings:
gm.glider.Cd=0.14 # trial. It goes a bit too fast
gm.glider.S=0.1 
#
gm.glider.Tref=20.
gm.glider.Sref=37.
gm.glider.alpha=1.05e-4
gm.glider.beta=7.81e-4
gm.glider.rhoConst=1028.
gm.glider.m=58.00-gm.glider.mb
gm.glider.V=58.00/1028.
# define a temperature and salinity profile:
gm.glider.set_salinity_profile([0,1000],[36,38])
gm.glider.set_temperature_profile([0,1000],[20,20])
#
gm.loadmission()
# run it until next expected surfacing
gm.run(dt=4,ndtCPU=1,end_on_surfacing=True)
#gm.run(dt=4,ndtCPU=1,maxSimulationTime=0.2)
d=np.array(gm.data.get("m_depth"))
t=np.array(gm.data.get("m_present_time"))

mspeed=np.array(gm.data.get("m_speed"))
xspeed=np.array(gm.data.get("x_speed"))
ue=np.array(gm.data.get("x_eastward_glider_velocity"))
un=np.array(gm.data.get("x_northward_glider_velocity"))
