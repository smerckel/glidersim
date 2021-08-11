from collections import deque
import math
from latlonUTM import UTM2latlon, latlon2UTM
from latlon import convertToNmea, convertToDecimal
import glob
import numpy as np
from timeconversion import strptimeToEpoch
import gliderflight
import random
import logging

logger = logging.getLogger(name="glidermodels")
logger.setLevel(logging.INFO)

class GliderException(Exception): pass

class GPS(object):
    def __init__(self,acquiretime=30):
        self.acquiretime=acquiretime
        self.status=2
        self.time=None
        self.enabled=False

    def enable(self):
        self.enabled=True
    def disable(self):
        self.enabled=False

    def get_status(self,t,z):
        if z<-.1: # underwater
            self.status=2
            self.time=t
        else:
            if not self.time:
                self.time=t
            if t-self.time>self.acquiretime:
                self.status=0
            else:
                self.status=1
        if not self.enabled:
            self.status*=(-1)
        return self.status

class PID(object):
    def __init__(self,Kp=1.,Ki=1.0,Kd=1.0):
        self.Kp=Kp
        self.Ki=Ki
        self.Kd=Kd
        self.deadband=0 # no correction if abs(error)<deadband
        self.reset()

    def output(self,t,processVariable,setVariable):
        e=setVariable-processVariable
        if abs(e)<self.deadband:
            return 0 # don't do anything
        if self.t:
            dedt=(e-self.e)/(t-self.t)
            self.ecum+=e*(t-self.t)
        else:
            dedt=0
        Pout=self.Kp*e
        Iout=self.Ki*self.ecum
        Dout=self.Kd*dedt
        self.e=e
        self.t=t
        return Pout+Iout+Dout

    def reset(self):
        self.t=None
        self.ecum=0
        self.e=0.


class LinearActuator(object):
    def __init__(self,
                 initial_position=0.,
                 speed=0.1,
                 position_max=1.,
                 position_min=-1.,
                 deadbandWidth=0.2):
        self.position=initial_position
        self.speed=speed
        self.position_max=position_max
        self.position_min=position_min
        self.deadbandWidth=deadbandWidth
        self.position_target=0.
        self.status=0   # 1 running <0 error, todo

    def set_commanded(self,value):
        self.position_target=value
        if value>self.position_max:
            self.position_target=self.position_max
        if value<self.position_min:
            self.position_target=self.position_min
        return self.position_target

    def get_measured(self):
        return self.position
    
    def actuate(self,dt):
        delta_position=self.position_target-self.position
        if self.status==0 and abs(delta_position)>self.deadbandWidth:
            self.status=1
        if self.status==1:
            speed=self.speed*(2*int(delta_position>0)-1)
            # a hack to prevent over shoots.
            if abs(delta_position)<abs(speed)*dt:
                factor=abs(delta_position/speed/dt)
            else:
                factor=1

            speed+=(random.random()-0.5)*speed*0.05
            self.position+=speed*dt*factor
            delta_position=self.position_target-self.position
            if (speed>0 and delta_position<=0) or \
                    (speed<0 and delta_position>=0):
                self.status=0 # switch off


class SlocumShallow100Hardware(object):
    def __init__(self):
        self.buoyancypump=LinearActuator(initial_position=200.,
                                         speed=32., # from data 
                                         position_max=233.,
                                         position_min=-233.,
                                         deadbandWidth=10.)
        self.pitchmotor=LinearActuator(initial_position=0.9,
                                       speed=0.10, # from data
                                       position_max=1,
                                       position_min=-1,
                                       deadbandWidth=0.05)
        self.finmotor=LinearActuator(0.,0.02,0.45,-0.45,0.035)
        self.finPID=PID(Kp=0.8,Ki=0.001,Kd=0)
        self.pitchPID=PID(Kp=0.4,Ki=0.0,Kd=0.0)

class SlocumDeepHardware(object):
    def __init__(self):
        self.buoyancypump=LinearActuator(initial_position=200.,
                                         speed=4., # from data 
                                         position_max=263.,
                                         position_min=-263.,
                                         deadbandWidth=30.)
        self.pitchmotor=LinearActuator(initial_position=0.9,
                                       speed=0.10, # 
                                       position_max=1.4,
                                       position_min=-1.4,
                                       deadbandWidth=0.02)
        self.finmotor=LinearActuator(0.,0.02,0.45,-0.45,0.035)
        self.finPID=PID(Kp=0.8,Ki=0.001,Kd=0)
        self.pitchPID=PID(Kp=0.4,Ki=0.001,Kd=0.0)


class SlocumDeepExtendedHardware(object):
    def __init__(self):
        self.buoyancypump=LinearActuator(initial_position=200.,
                                         speed=4., # from data 
                                         position_max=400.,
                                         position_min=-400.,
                                         deadbandWidth=30.)
        self.pitchmotor=LinearActuator(initial_position=0.9,
                                       speed=0.10, # 
                                       position_max=1.4,
                                       position_min=-1.4,
                                       deadbandWidth=0.02)
        self.finmotor=LinearActuator(0.,0.02,0.45,-0.45,0.035)
        self.finPID=PID(Kp=0.8,Ki=0.001,Kd=0)
        self.pitchPID=PID(Kp=0.4,Ki=0.001,Kd=0.0)

        

class BaseGliderModel(object):
    def __init__(self):
        self.gps=GPS()
        self.gliderflight_model =  GliderFlightModel()

        # Glider Hardware, to be subclassed.
        self.buoyancypump = None
        self.pitchmotor = None
        self.finmotor = None
        #
        self.environment_model = None # to be set later.
        self._speed_deque = deque(maxlen=60//4) # used for moving avg of speed.
        
    def initialise_gliderflightmodel(self, Cd0, Vg, mg, T1=1235, T2=-28.8, T3=0.14, T4=0, **kwds):
        gfm = self.gliderflight_model
        gfm.define(Cd0=Cd0)
        gfm.define(Vg=Vg)
        gfm.define(mg=mg)
        gfm.pitch_model_parameters = (T1, T2, T3, T4)
        if kwds:
            gfm.define(**kwds)
        
                
    def initialise_gliderstate(self,datestr,timestr,lat,lon, mission_start):
        self.lmc_x = 0
        self.lmc_y = 0
        self.lmc_z = 0
        self.x = self.y = self.z = 0 # real coordinates

        gs={}
        gs['m_depth']=0
        gs['m_present_secs_into_mission']=0.
        gs['samedepth_for']=0
        if datestr:
            if timestr:
                gs['m_present_time']=strptimeToEpoch(datestr+timestr,"%Y%m%d%H:%M")
            else:
                gs['m_present_time']=strptimeToEpoch(datestr,"%Y%m%d")
        else:
            gs['m_present_time']=0.
        gs['stack']=1 # number of commands given.
        gs['bpump_stack']=0
        gs['fin_stack']=0 
        gs['pitch_stack']=0 
        gs['m_ballast_pumped']=0.
        gs['m_dist_to_wpt']=0.
        gs['c_ballast_pumped']=230
        gs['c_battpos']=1
        gs['c_fin']=0
        gs['m_fin']=0
        gs['m_pitch']=0.
        gs['c_pitch']=0.
        gs['m_altitude']=1e9
        gs['hover_for']=0
        gs['stalled_for']=0
        if lat:
            gs['m_lat']=lat
        else:
            gs['m_lat']=0
        if lon:
            gs['m_lon']=lon
        else:
            gs['m_lon']=0
        gs['m_lmc_x']=0
        gs['m_lmc_y']=0
        gs['c_wpt_lat']=-1.
        gs['c_wpt_lon']=-1.
        gs['c_wpt_lmc_x']=0
        gs['c_wpt_lmc_y']=0
        gs['m_dist_to_wpt']=9e9
        gs['m_heading']=0.
        gs['m_heading_rate']=0.
        gs['m_battpos']=0.
        gs['c_heading']=0
        gs['nocomms']=0
        gs['time_since_cycle_start']=0
        gs['x_lmc_x']=0
        gs['x_lmc_y']=0
        gs['x_lmc_z']=0
        gs['m_gps_status']=0
        gs['c_gps_on']=0
        if lat and lon:
            utm_0=latlon2UTM(convertToDecimal(lat),
                             convertToDecimal(lon))
        else:
            utm_0 = None
        gs['utm_0'] = utm_0
        gs['x_u']=0.
        gs['x_v']=0.
        gs['x_w']=0.
        gs['temp']=0.
        gs['salt']=0.
        gs['rho']=0.
        gs['water_depth']=0.
        gs['m_speed']=0.
        gs['x_speed']=0.
        gs['u_use_current_correction']=0
        gs['m_water_vx']=0.
        gs['m_water_vy']=0.
        gs['keep_stack_busy']=0
        gs['x_gps_lmc_x_dive']=0
        gs['x_gps_lmc_y_dive']=0
        gs['x_time_dive']=0
        gs['_init_dive_time']=80. # time for glider to open files/init devices. etc.
        gs['x_lat']=0
        gs['x_lon']=0
        gs['x_water_depth']=0
        gs['x_last_wpt_lat']=69696969.
        gs['x_last_wpt_lon']=69696969.
        gs['x_eastward_glider_velocity']=0.
        gs['x_northward_glider_velocity']=0.
        gs['x_upward_glider_velocity']=0.
        gs['m_segment_number']=0
        gs['_pickup']=(mission_start=="pickup") # If true, then
                            # c_wpt_* will be set by specified sensors
                            # during start of the mission, rather than
                            # from the waypoint list algorithm,
                            # mimicking the continuation of the the
                            # mission. This affects the behavior
                            # goto_l
        gs['m_mission_start_time'] = gs['m_present_time']
        gs['m_pressure'] = 0
        gs['x_lmc_x_wpt_calc'] = 0 # stores start point of transect, used to calculate heading from waypoints.
        gs['x_lmc_y_wpt_calc'] = 0
        self.gs=gs


    def translate_lmc_latlon(self,x,y):
        (east,north),z0,z1=self.gs['utm_0']
        east+=x
        north+=y
        latlon=UTM2latlon(z0,z1,east,north)
        lat=convertToNmea(latlon[0])
        lon=convertToNmea(latlon[1])
        return lat,lon

    def get_environmental_data(self, t, lat, lon, z):
        '''Method to get environmental data. 
        Should be provided by a subclassed instance.
        For now, return some sensible values to keep going.

        When subclassed, this method should check for the
        reasonability of the values to be returned.
        '''

        if self.environment_model is None:
            u_ocean = v_ocean = w_ocean = 0
            S =35
            T=15
            eta = 0
            water_depth = 40
            rho = 1025
            return u_ocean, v_ocean, w_ocean, water_depth, eta, S, T, rho
        else:
            declat = convertToDecimal(lat)
            declon = convertToDecimal(lon)
            return self.environment_model.get_data(t, declat, declon, z)
    
    def update(self,t,dt):
        self.gs['m_gps_status']=self.gps.get_status(self.gs['m_present_time'],self.z)
        if self.gs['c_gps_on']: 
            self.gps.enable() 
        else: 
            self.gps.disable()
        #
        self.pitchmotor.actuate(dt)
        self.buoyancypump.actuate(dt)
        self.finmotor.actuate(dt)
        #
        self.gs['m_ballast_pumped']=self.buoyancypump.get_measured()
        self.gs['m_fin']=self.finmotor.get_measured()
        self.gs['m_battpos']=self.pitchmotor.get_measured()
        #
        realLat,realLon=self.translate_lmc_latlon(self.x,self.y)
        u, v, w, water_depth, eta, S, T, rho = self.get_environmental_data(t,realLat,realLon,self.z)

        # set glider parameters
        self.gs['temp']=T
        self.gs['salt']=S
        self.gs['water_depth']=water_depth
        self.gs['rho']= rho
        self.gs['x_u']=u
        self.gs['x_v']=v
        self.gs['x_w']=w
        self.gs['x_water_depth']=water_depth+eta

        # for the CTD, we have only temperature. We would need to back-calculate C
        
        # compute heading and heading_rate from fin position, and pitch:

        p = [self.gs[i] for i in 'm_present_time m_heading m_heading_rate m_fin m_speed'.split()]
        m_heading, m_heading_rate = self.gliderflight_model.compute_heading_from_fin(*p)

        p = [self.gs[i] for i in 'm_battpos m_ballast_pumped m_pressure'.split()]
        m_pitch = self.gliderflight_model.compute_pitch_from_battpos_buoyancy_drive(*p)

        # update glider state with new variables:

        self.gs['m_heading'] = m_heading
        self.gs['m_heading_rate'] = m_heading_rate
        self.gs['m_pitch'] = m_pitch

        # compute the new dynamic status of the glider.
        tmp = self.gliderflight_model.step_integrate(self.x,
                                                     self.y,
                                                     self.z,
                                                     self.gs['x_eastward_glider_velocity'],
                                                     self.gs['x_northward_glider_velocity'],
                                                     self.gs['x_upward_glider_velocity'],
                                                     m_pitch,
                                                     rho,
                                                     self.gs['m_ballast_pumped'],
                                                     m_heading)
        self.x, self.y, self.z, self.gs['x_eastward_glider_velocity'],\
            self.gs['x_northward_glider_velocity'], self.gs['x_upward_glider_velocity'] = tmp

        speed = (self.gs['x_eastward_glider_velocity']**2 + self.gs['x_northward_glider_velocity']**2)**0.5
        self.gs['x_speed']=speed
        # use Kalman filter to estiamte running average
        if speed>0: # not at the surface
            self._speed_deque.append(speed)
            self.gs['m_speed']=np.mean(self._speed_deque)
                            

        # update real position of the glider:
        self.x += u * dt
        self.y += v * dt
        self.z += w * dt        

        # update new position (dead reckoned)
        self.gs['m_depth'] = - self.z
        self.gs['m_pressure'] = max(0, -self.z * rho *9.81 * 1e-5)
        if self.gs['m_gps_status']==0:
            # at the surface, and got a signal.
            self.lmc_x=self.x
            self.lmc_y=self.y
        else:
            self.lmc_x += dt * self.gs['x_northward_glider_velocity']
            self.lmc_y += dt * self.gs['x_eastward_glider_velocity']
        if self.gs['u_use_current_correction']:
            self.lmc_x += dt * self.gs['m_water_vx']
            self.lmc_y += dt * self.gs['m_water_vy']
            
        self.gs['m_lmc_x']=self.lmc_x
        self.gs['m_lmc_y']=self.lmc_y
        #
        self.gs['m_lat'],self.gs['m_lon']=self.translate_lmc_latlon(self.lmc_x,self.lmc_y)

        m_depth_rate = self.gs['x_upward_glider_velocity']
        if abs(m_depth_rate)<1e-4:
            self.gs['samedepth_for']+=dt
            if self.z>0.1:
                self.gs['hover_for']+=dt
                self.gs['stalled_for']+=dt
        else:
            self.gs['samedepth_for']=0
            self.gs['hover_for']=0
            self.gs['stalled_for']=0
        self.gs['m_altitude']=water_depth-self.gs['m_depth']
        self.gs['m_present_time']+=dt
        self.gs['m_present_secs_into_mission']+=dt
        self.gs['nocomms']+=dt
        self.gs['time_since_cycle_start']+=dt
        # store real glider positions too.
        self.gs['x_lmc_x']=self.x
        self.gs['x_lmc_y']=self.y
        self.gs['x_lmc_z']=self.z
        self.gs['x_lat'],self.gs['x_lon']=self.translate_lmc_latlon(self.x,self.y)        

    def calibrate(self,Vdown,Vup,T,S):
        raise ValueError("Obsolete?")
        bps=np.arange(-1,1,0.1)
        pitchDown=[]
        pitchUp=[]
        self.gs['temp']=T
        self.gs['salt']=S
        for bp in bps:
            self.set_parameters(Vdown,bp,0,10,4)
            pitchDown.append(self.m_pitch)
            self.set_parameters(Vup,bp,0,10,4)
            pitchUp.append(self.m_pitch)
        return np.array(pitchDown),np.array(pitchUp)


    
class FinModel(object):
    def __init__(self, c0=0.5, c1=15.):
        self.c0 = c0
        self.c1 = c1
        self.sigma_noise=0.01

    def noise(self):
        return np.random.normal(loc=0, scale=self.sigma_noise)
    
    def compute_heading_rate(self, dt, m_fin, m_speed, m_heading_rate):
        m_fin += self.noise()
        
        m_heading_rate = self.c0/self.c1*np.sin(m_fin)*m_speed**2*dt + m_heading_rate*(1-dt/2/self.c1)
        m_heading_rate /= 1+dt/2/self.c1

        return m_heading_rate
    

    
    
class GliderFlightModel(gliderflight.DynamicGliderModel):
    ''' Flight model based on glider flight.

    This class inherits from the DynamicGliderModel class, but implements a new method step_integrate(), 
    meant to compute a new speed *and position* for a single time step. 
    '''
    def __init__(self, dt=None, rho0=None, k1=0.20, k2=0.92, alpha_linear=90, alpha_stall=90,
                 max_depth_considered_surface=0.5):
        super().__init__(dt, rho0, k1, k2, max_depth_considered_surface=max_depth_considered_surface)
        self.pitch_model_parameters=(1235,-28.8, 0.138, 0) # T1, T2, T3 and T4from glidertrim program.
        self.fin_model = FinModel()
        
    def step_integrate(self, x, y, z, u, v, w, pitch, rho, buoyancy_change, heading):
        ''' Integrate the equations for a single time step.

        Parameters
        ----------
        x : position in LMC (m), east
        y : position in LMC (m), north
        z : position in LMC (m), vertical (positive up, z=0 corresponds to surface)
        u : eastward velocity
        v : northward velocity
        w : upward velocigty
        pitch: pitch (rad)
        rho : density (kg m^{-3})
        buoyancy_change (cc)
        heading (rad, heading=0 corresponds to North)

        Returns
        -------
        x, y, z, y, v, w : updated parameters (description as in input)
        '''
        
        h = self.dt
        pressure = max(-z/10,0) # in bar
        pressure, Vbp = self.convert_pressure_Vbp_to_SI(pressure, buoyancy_change)
        FB, Fg = self.compute_FB_and_Fg(pressure, rho, Vbp, self.mg, self.Vg)
        M = self.compute_inverted_mass_matrix(pitch)
        threshold = self.max_depth_considered_surface * 1e4 # in Pa.

        at_surface = pressure<threshold
        FBg = FB-Fg
        m11, m12, m21, m22 = M
        uh = np.sqrt(u**2 + v**2)
        
        Cd0 = self.Cd0
        # stage 1
        k1_u, k1_w = self._DynamicGliderModel__compute_k(uh, w, rho, pitch, FBg, m11, m12, m21, m22, h, Cd0)
        k1_sx = h * uh
        k1_sz = h * w
        _uh = uh + k1_u*0.5
        _w = w + k1_w*0.5
        # stage 2
        k2_u, k2_w = self._DynamicGliderModel__compute_k(_uh, _w, rho, pitch, FBg, m11, m12, m21, m22, h, Cd0)
        k2_sx = h * _uh
        k2_sz = h * _w
        # stage 3
        _uh = uh + k2_u*0.5
        _w = w + k2_w*0.5
        k3_u, k3_w = self._DynamicGliderModel__compute_k(_uh, _w, rho, pitch, FBg, m11, m12, m21, m22, h, Cd0)
        k3_sx = h * _uh
        k3_sz = h * _w
        #stage 4
        _uh = uh + k3_u
        _w = w + k3_w
        k4_u, k4_w = self._DynamicGliderModel__compute_k(_uh, _w, rho, pitch, FBg, m11, m12, m21, m22, h, Cd0)
        k4_sx = h * _uh
        k4_sz = h * _w
        uh += (k1_u + 2*k2_u + 2*k3_u + k4_u)/6
        w += (k1_w + 2*k2_w + 2*k3_w + k4_w)/6
        sx = (k1_sx + 2*k2_sx + 2*k3_sx + k4_sx)/6
        sz = (k1_sz + 2*k2_sz + 2*k3_sz + k4_sz)/6

        if z+sz>0: # at the surface
            sx=uh=w=0
            sz = -z # so we get exactly at the surface.
            
        hdg = np.pi/2 - heading
        u = np.cos(hdg) * uh
        v = np.sin(hdg) * uh
        x += sx * np.cos(hdg)
        y += sx * np.sin(hdg)
        z += sz
        return x, y, z, u, v, w

    def compute_heading_from_fin(self, t, heading, heading_rate, m_fin, m_speed):
        heading_rate = self.fin_model.compute_heading_rate(self.dt, m_fin, m_speed, heading_rate)
        heading += heading_rate * self.dt
        heading %= np.pi*2
        return heading, heading_rate

    def compute_pitch_from_battpos_buoyancy_drive(self, m_battpos, m_ballast_pumped, m_pressure):
        battpos = m_battpos*2.56e-2 # m
        Vp = m_ballast_pumped*1e-6  # m^3
        P = m_pressure * 1e-3        # kbar
        T1, T2, T3, T4 = self.pitch_model_parameters
        tanpitch=T1*Vp + T2*battpos + T3 + T4 * P
        return np.arctan(tanpitch)


   
# subclasses of BaseGliderModel
class Shallow100mGliderModel(BaseGliderModel, SlocumShallow100Hardware):
    def __init__(self):
        logger.info("Initialising SLOCUM 100 m glider")
        BaseGliderModel.__init__(self)
        SlocumShallow100Hardware.__init__(self)

class DeepGliderModel(BaseGliderModel,SlocumDeepHardware):
    def __init__(self):
        logger.info("Initialising SLOCUM 1000 m glider")
        BaseGliderModel.__init__(self)
        SlocumDeepHardware.__init__(self)

class DeepExtendedGliderModel(BaseGliderModel,SlocumDeepExtendedHardware):
    def __init__(self):
        logger.info("Initialising SLOCUM 1000 m glider with Extended buoyancy pump")
        BaseGliderModel.__init__(self)
        SlocumDeepHardware.__init__(self)

        



        
