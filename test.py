import glidersim
import glidersim.configuration
import glidersim.getm

# setting the name for U and V velocities as used int he getm data files.
glidersim.getm.GetmEnvironment.Uname='eastward_sea_water_velocity'
glidersim.getm.GetmEnvironment.Vname='northward_sea_water_velocity'
glidersim.getm.GetmEnvironment.UseW=False


conf = glidersim.configuration.Config('helgo.mi',
                                      description="for comparing with real glider data",
                                      datestr='20120905',
                                      timestr='16:06',
                                      lat_ini=5432.496,
                                      lon_ini=725.716,
                                      output='helgo-compare.pck',
                                      sensorSettings=[('u_use_current_correction',0)],
                                      specialSettings=['glider.gps.acquiretime=100.'],
                                      directory='/home/lucas/getm_data/getm3d',
                                      storePeriod=1)
#


class GetmGliderModel(glidersim.glidermodels.SimpleDynamics,
                      glidersim.glidermodels.GliderModel,
                      glidersim.getm.GetmEnvironment):

    def __init__(self,datestr,timestr,lat,lon,**kwds):
        if "pitch_model_parameters" in kwds.keys():
            pitch_model_parameters=kwds["pitch_model_parameters"]
        else:
            pitch_model_parameters=(1300,-30,0.)
        glidersim.glidermodels.SimpleDynamics.__init__(self,x=0,y=0,
                                                       pitch_model_parameters=pitch_model_parameters)
        glidersim.glidermodels.GliderModel.__init__(self,datestr,timestr,lat,lon)
        print("Glider simulation start coordinates:",datestr,timestr,lat,lon)
        glidersim.getm.GetmEnvironment.__init__(self,
                                                kwds['directory'],
                                                kwds['basename'],
                                                kwds['suffix'])



GM=glidersim.glidersim.GliderMission(conf,interactive=False,glidermodel=GetmGliderModel)
# set overall glider mass to 51.65 kg (was 51.80)
GM.glider.m= 51.55 - GM.glider.mb                                     


GM.loadmission(verbose=False)
#GM.run(dt=1.,ndtCPU=4,maxSimulationTime=1./2.)
#GM.save()
