from . import glidermodels
from . import behaviors
from . import parser
from math import atan2, pi,sqrt
from . import datastore
import numpy as np
import os
from .glidermodels import GliderException

MISSIONS = 'missions'
MAFILES = 'mafiles'

class Actuator(object):
    busy=False
    def __init__(self):
        self.commanded=None
    def set_busy(self,arg=True):
        self.busy=arg
    def get_stack(self):
        if self.busy:
            return 1
        if self.commanded:
            return 1
        else:
            return 0

class Controls(object):
    def __init__(self):
        self.cmd={'c_ballast_pumped':'pump',
                  'c_battpos':'pitch_motor',
                  'c_pitch':'pitch_motor',
                  'c_heading':'fin',
                  'c_wpt_latlon':'fin',
                  'c_fin':'fin'}
        actuators=['pump','pitch_motor','fin']
        self.actuator=dict((k,Actuator()) for k in actuators)

    def set(self,cmdval):
        actuatorName=self.cmd[cmdval[0]]
        self.actuator[actuatorName].commanded=cmdval

    def reset(self):
        for k in list(self.actuator.keys()):
            self.actuator[k].commanded=None



class LayeredControl(object):
    def __init__(self):
        self.stack=[]
        self.controls=Controls()
        self.finPID=None
        self.pitchPID=None
    
    def set_PIDS(self,finPID,pitchPID):
        self.finPID=finPID
        self.pitchPID=pitchPID

    def addBehavior(self,beh):
        beh.init()
        self.stack.append(beh)
        

    def cycle(self,gs):
        if behaviors.Behavior.MS>=4:
            # don't let the states set b, p and f if aborting
            b=-100. # clips?
            p=1000. # clips
            f=0.
        else:
            # all is fine, let state engine set b, p and f
            for b,beh in enumerate(self.stack):
                behaviors.CLRS.g("processing "+beh.behaviorName+ "(%d)"%(b))
                beh.process(gs)   # new values here
                behaviors.CLRS.g("processing "+beh.behaviorName+ "(%d) Done"%(b))
                for i in beh.fsm.memory:
                    if i and i[1]: # exclude when value is None
                        self.controls.set(i)
                Actuator.busy=bool(gs['keep_stack_busy'])
                gs['bpump_stack']=self.controls.actuator['pump'].get_stack()
                gs['fin_stack']=self.controls.actuator['fin'].get_stack()
                gs['pitch_stack']=self.controls.actuator['pitch_motor'].get_stack()
                gs['stack']=gs['bpump_stack']+gs['pitch_stack']
            b,p,f=self.resolve(gs)
            self.controls.reset()
        return b,p,f

    def resolvePitch(self,c_pitch,m_pitch,c_battpos,t):
        delta_battpos=-self.pitchPID.output(t,np.tan(m_pitch),np.tan(c_pitch))
        x_battpos=c_battpos+delta_battpos
        return x_battpos

    def resolveHeading(self,c_heading,m_heading,t):
        if c_heading-m_heading<pi : m_heading-=2*pi
        if c_heading-m_heading>pi : m_heading+=2*pi
        x_fin=self.finPID.output(t,m_heading,c_heading)
        # clips if too large.
        return x_fin
            
    def resolveWpt(self,c_wpt,m_lmc_x,m_lmc_y,
                   use_current_correction,m_speed,vx,vy):
        dy=c_wpt[1]-m_lmc_y
        dx=c_wpt[0]-m_lmc_x
        if use_current_correction and vx and vy:
            distanceToWaypoint=sqrt(dx**2+dy**2)
            timeToWaypoint=distanceToWaypoint/max(0.1,m_speed)
            cdx=timeToWaypoint*vx
            cdy=timeToWaypoint*vy
        else:
            cdx=0
            cdy=0
        phi=atan2(dy-cdy,dx-cdx)
        c_heading=-phi+pi/2.
        return c_heading%(2.*pi)
        
    def resolve(self,gs):
        c_battpos=gs['c_battpos']
        c_ballast_pumped=gs['c_ballast_pumped']
        c_fin=gs['c_fin']
        c_battpos=None
        c_ballast_pumped=None
        c_fin=None
        t=gs['m_present_time']

        cmd=self.controls.actuator['pitch_motor'].commanded
        if cmd:
            if cmd[0]=='c_pitch':
                c_pitch=cmd[1]
                c_battpos=self.resolvePitch(c_pitch,gs['m_pitch'],
                                            gs['c_battpos'],t)
                gs['c_battpos']=c_battpos
                gs['c_pitch']=c_pitch
            elif cmd[0]=='c_battpos':
                c_battpos=cmd[1]
                gs['c_battpos']=c_battpos
            else:
                raise ValueError("unknown pitch control")
            
        cmd=self.controls.actuator['pump'].commanded
        if cmd:
            if cmd[0]=='c_ballast_pumped':
                c_ballast_pumped=cmd[1]
                gs['c_ballast_pumped']=c_ballast_pumped
            else:
                raise ValueError("unknown pump control")

        cmd=self.controls.actuator['fin'].commanded
        if cmd:
            if cmd[0]=='c_fin':
                c_fin=cmd[1]
            elif cmd[0]=='c_heading':
                c_fin=self.resolveHeading(cmd[1],gs['m_heading'],t)
            elif cmd[0]=='c_wpt_latlon':
                c_heading=self.resolveWpt(cmd[1],gs['m_lmc_x'],gs['m_lmc_y'],
                                          gs['u_use_current_correction'],
                                          gs['m_speed'],
                                          gs['m_water_vx'],
                                          gs['m_water_vy'])
                gs['c_heading']=c_heading
                c_fin=self.resolveHeading(c_heading,gs['m_heading'],t)
            else:
                raise ValueError("unknown fin control")
            gs['c_fin']=c_fin
        return c_battpos,c_ballast_pumped,c_fin




            
class GliderMission(datastore.Data):
    def __init__(self,config,glidermodel=None,environment_model=None, interactive=True):
        if interactive:
            config.checkOutputFilename()
        if glidermodel is None:
            raise ValueError("No glider model specified. Try ShallowGliderModel for example.")
        
        datestr=config.datestr
        timestr=config.timestr
        lat=config.lat_ini
        lon=config.lon_ini
        dt = config.dt
        rho0 = config.rho0
        mission_start = config.mission_start
        
        self.mission=config.missionName
        self.mission_directory=config.mission_directory
        self.output=config.output
        self.longtermParameters=config.longtermParameters

        self.datatransfertime=0.

        self.glider=glidermodel(dt, rho0, environment_model)
        self.glider.initialise_gliderstate(datestr, timestr, lat, lon, mission_start)
        self.glider.initialise_gliderflightmodel(Cd0=config.Cd0,
                                                 ah=config.ah,
                                                 Vg=config.Vg,
                                                 mg=config.mg,
                                                 T1 = config.T1,
                                                 T2 = config.T2,
                                                 T3 = config.T3)
        self.LC=LayeredControl()
        # set the PIDs for LC, as they are hardware dependent:
        self.LC.set_PIDS(self.glider.finPID,self.glider.pitchPID)
        config.set_sensors(self)
        config.set_special_settings(self)
        datastore.Data.__init__(self,self.glider.gs,period=config.storePeriod)

    def loadlongterm(self,longterm_filename=None):
        if longterm_filename!=None:
            if os.path.exists(longterm_filename):
                fd=open(longterm_filename,'r')
                lines=fd.readlines()
                fd.close()
                for line in lines:
                    words=line.split()
                    parameter=words[0]
                    if parameter not in self.longtermParameters:
                        self.longtermParameters.append(parameter)
                    value=float(words[1])
                    self.sensor(parameter,value)
                    print("setting: ",line)

    def savelongterm(self,longterm_filename=None):
        if longterm_filename!=None:
            fd=open(longterm_filename,'w')
            for p in self.longtermParameters:
                fd.write("%s %f\n"%(p,self.glider.gs[p]))
            fd.close()
            print("Longterm state file successfully written.")
        
    def loadmission(self,mission=None,verbose=True):
        if not mission:
            if not self.mission:
                raise ValueError("No mission name supplied!")
            else:
                mission=self.mission
        mission = os.path.join(self.mission_directory, MISSIONS, mission)
        mafiles_directory = os.path.join(self.mission_directory, MAFILES)

        
        MP=parser.MissionParser(verbose=verbose)
        MP.parse(mission, mafiles_directory)
        # set sensor_settings, if any
        for p,v in MP.sensor_settings:
            self.sensor(p,v)
        MP.behaviors.reverse()
        for b in MP.behaviors:
            if isinstance(b,behaviors.Surface) \
                    and hasattr(self,"datatransfertime"):
                b.datatransfertime=self.datatransfertime
            self.LC.addBehavior(b)
            if verbose:
                b.printInfo()

    def get(self,parameter):
        return np.asarray(self.data[parameter])

    def sensor(self,parameter,value):
        if parameter in self.glider.gs:
            if value==None:
                print("Setting sensor %s failed (value==None)"%(parameter))
            else:
                print("setting sensor value %s=%f"%(parameter,value))
                self.glider.gs[parameter]=value
        else:
            print("Ignoring sensor setting %s (sensor is not used)"%(parameter))

    def check_if_on_surface(self):
        r=False
        for s in self.LC.stack:
            if s.behaviorName=='Surface' and s.get_current_state()=='WaitForUser':
                r=True
                break
        return r
            
    def run(self,dt=1,CPUcycle=4,maxSimulationTime=None,
            end_on_surfacing=0):
        ''' dt : time step in seconds
            CPUcycle: time step per CPU cycle.
            maxSimulationTime: maximum simulation time in days

            end_on_surfacing n>0:
            Stops simulation when glider surfaces via a surfacing 
            behavior for nth time.
        '''
        if self.glider.gs['_pickup'] == True: # we're continuing an existing mission (affects goto_l behavior only)
            self.glider.gs['time_since_cycle_start']=self.datatransfertime

        behaviors.Behavior.MS=0
        # surface conditions:
        self.glider.gs['c_ballast_pumped']=self.glider.buoyancypump.set_commanded(1000)        
        self.glider.gs['c_battpos']=self.glider.pitchmotor.set_commanded(100)
        self.glider.gs['c_fin']=self.glider.finmotor.set_commanded(0)        
        subcycle_time = 1e3 # make sure we update LC on the first round.
        simulationTime = self.glider.gs['m_present_time']
        while 1:
            if behaviors.VERBOSE==True:
                print("Time:", simulationTime)
                print("m_depth:", self.glider.gs['m_depth'])
                print("hover for:", self.glider.gs['hover_for'])
                print("pitch stack:",self.glider.gs['pitch_stack'])
                print("pump stack:",self.glider.gs['bpump_stack'])
                print("fin stack:",self.glider.gs['fin_stack'])
                print("ballast pumped:",self.glider.gs['c_ballast_pumped'],self.glider.gs['m_ballast_pumped'])
                print()
                
            if subcycle_time>CPUcycle: # a new cpucycle
                b,p,f=self.LC.cycle(self.glider.gs)
                subcycle_time=0
            if self.glider.gs['m_depth']<0.1: # at the surface:
                f=0 # set fin to 0
                self.LC.finPID.reset() # reset PID settings (ecum ->0)
            if behaviors.Behavior.MS&behaviors.TOQUIT:
                # end of missioin signaled. Come to the surface, no matter what...
                b=-10.
                p=1000.
                f=0.
            if p!=None:
                self.glider.gs['c_ballast_pumped']=self.glider.buoyancypump.set_commanded(p)        
            if b!=None:
                self.glider.gs['c_battpos']=self.glider.pitchmotor.set_commanded(b)
            if f!=None: 
                self.glider.gs['c_fin']=self.glider.finmotor.set_commanded(f)        
            if behaviors.Behavior.MS&behaviors.TOQUIT and self.glider.gs['m_depth']<0.1:
                behaviors.Behavior.MS+= ~behaviors.Behavior.MS&behaviors.COMPLETED # setting COMPLETED flag
            if behaviors.Behavior.MS&behaviors.COMPLETED or \
                    (behaviors.Behavior.MS>=8 and self.glider.gs['m_depth']<0.1):
                break

            if self.glider.gs['m_depth']>1300:
                raise ValueError('Whoops! Sinking to the depths...!')
            if maxSimulationTime and self.glider.gs['m_present_secs_into_mission']>maxSimulationTime*86400.:
                print("Mission exceeding simulation time.") 
                break

            if end_on_surfacing:
                if self.check_if_on_surface():
                    print("Glider is on surface...", end=' ')
                    end_on_surfacing-=1
                    if end_on_surfacing==0:
                        print("Ending mission")
                        self.add_data(force_data_write=True)
                        break
                    else:
                        print("Continuing")

            self.glider.update(simulationTime,dt)
            self.add_data()
            simulationTime+=dt
            subcycle_time+=dt
            
        # mission is finialised. End of while 1:

        if behaviors.Behavior.MS&behaviors.COMPLETED:
            print("Mission completed.")
        else:
            for k,v in behaviors.ABORTS.items():
                if behaviors.Behavior.MS&v:
                    print("Mission abort: %s"%(k.upper()))

if __name__=='__main__':
    GM=GliderMission('gb.mi',datestr='20100519',timestr="00:30",lat=5410.000,lon=800.000,
                     directory='nc')
    GM.loadmission()
    input("Enter to start")
    GM.run()
    GM.save('run.pck')

    t=np.asarray(GM.data['m_present_secs_into_mission'])
    y=-np.asarray(GM.data['m_depth'])
    rho=np.asarray(GM.data['rho'])
