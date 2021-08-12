from math import sqrt,pi,sin,cos
from functools import reduce
from collections import UserList, OrderedDict

import arrow

import latlon

from .fsm import FSM
from . import common

logger = common.get_logger("behaviors")

INPROGRESS=1
TOQUIT=2
COMPLETED=4
ABORT_OVERTIME=8
ABORT_OVERDEPTH=16
ABORT_SAMEDEPTH_FOR=32
ABORT_STACK_IDLE=64


ABORTS={'overtime':ABORT_OVERTIME,
        'overdepth':ABORT_OVERDEPTH,
        'samedepth_for':ABORT_SAMEDEPTH_FOR,
        'stack_idle':ABORT_STACK_IDLE}

VERBOSE=False
#VERBOSE=True

class CLRS:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    @classmethod    
    def __prt__(self,str):
        if VERBOSE:
            logger.info(str)
    @classmethod
    def y(self,str):
        self.__prt__(CLRS.WARNING+str+CLRS.ENDC)

    @classmethod
    def r(self,str):
        self.__prt__(CLRS.FAIL+str+CLRS.ENDC)

    @classmethod
    def g(self,str):
        self.__prt__(CLRS.OKGREEN+str+CLRS.ENDC)

    @classmethod
    def b(self,str):
        self.__prt__(CLRS.OKBLUE+str+CLRS.ENDC)

    @classmethod
    def w(self,str):
        self.__prt__(str)

    @classmethod
    def m(self,str):
        self.__prt__(CLRS.HEADER+str+CLRS.ENDC)


class Condition(object):
    ''' defines a condition for the given parameter, with optional value range.
        for example: 
        
        c=Condition('m_present_time','>',0,(None,None))

        The class defines a method check() that returns True or False, depending on
        whether the current value of the parameter matches the condition or not.
    '''
    def __init__(self,parameter,operator,value,valuerange=(None,None),*args):
        self.parameter=[parameter]
        self.operator=[operator]
        self.value=[value]
        self.valuerange=[list(valuerange)]
        args=list(args)
        if len(args)>0:
            if len(args)%4:
                raise ValueError('Condition statement wrongly constructed')
            for j in range(int(len(args)/4)):
                self.parameter.append(args.pop(0))
                self.operator.append(args.pop(0))
                self.value.append(args.pop(0))
                self.valuerange.append(list(args.pop(0)))
        self.check_input()

    def check_input(self):
        for i,vr in enumerate(self.valuerange):
            if vr[0]==None:
                vr[0]=-1e12
            if vr[1]==None:
                vr[1]=1e12
            self.valuerange[i]=vr
        for i in self.operator:
            if i not in ['>','==','<','!=']:
                raise ValueError('Unknown comparison operator')
        #print "%s %s %s"%(parameter,operator,value)

    def addCondition(self,parameter,operator,value,valuerange=(None,None)):
        self.parameter.append(parameter)
        self.operator.append(operator)
        self.value.append(value)
        self.valuerange.append(list(valuerange))
        self.check_input()

    def check_param(self,gs,parameter,value,valuerange,operator):
        #print(f"Check param {parameter}, {value}, {valuerange}, {operator} Actual value: {gs[parameter]}", end='')
        if parameter not in gs:
            raise ValueError("glider status has not required parameter")
        if (value<=valuerange[1] and value>=valuerange[0]) or \
                value==None:
            r=eval("%s%s%s"%(gs[parameter],operator,value))
        else:
            r=False
        #print(f" Result: {r}")
        return r
    def check_params(self,gs):
        rs=[]
        for p,v,vr,o in zip(self.parameter,self.value,self.valuerange,self.operator):
            rs.append(self.check_param(gs,p,v,vr,o))
        return rs

    def check(self,gs):
        c=self.check_params(gs)
        return reduce(lambda x,y: x or y,c)

    # dummy methods: allow condition to be handles as Flag
    def set_True(self):
        pass
    def set_False(self):
        pass

class ConditionAnd(Condition):
    def __init__(self,parameter,operator,value,valuerange=(None,None),*args):
        Condition.__init__(self,parameter,operator,value,valuerange,*args)
    def check(self,gs):
        return reduce(lambda x,y: x and y,self.check_params(gs))

class ConditionOr(Condition):
    def __init__(self,parameter,operator,value,valuerange=(None,None),*args):
        Condition.__init__(self,parameter,operator,value,valuerange,*args)
    def check(self,gs):
        return reduce(lambda x,y: x or y,self.check_params(gs))
        

class Flag(object):
    def __init__(self,flag=True):
        self.flag=flag
    def set_True(self):
        self.flag=True
    def set_False(self):
        self.flag=False
    def check(self,*dmy):
        return self.flag

class UTC_Condition(object):
    def __init__(self,timetuple):
        self.min,self.hour,self.day,self.month=timetuple

    def __set(self,a,b):
        r=(a+1) or (b+1)
        return r-1

    def check(self,gs):
        t=gs['m_present_time']
        dt=arrow.get(t).datetime
        year = dt.year
        month = self.__set(self.month,dt.month)
        day = self.__set(self.day,dt.day)
        hour = self.__set(self.hour,dt.hour)
        minute = self.__set(self.min,dt.minute)
        s="%d%02d%02d %02d%02d"%(year,month,day,hour,minute)
        tc = arrow.get(s, "YYYYMMDD HH:mm").timestamp()
        if t>=tc and t<=tc+60.:
            return True
        else:
            return False

class UniqueList(UserList):
    def __init__(self, initlist=None):
        super().__init__(initlist)

    def __iadd__(self, x):
        for _x in x:
            if _x in self:
                continue
            else:
                self.append(_x)
        return self
            
###### Super class behaviors #######

class Behavior(object):
    MS=INPROGRESS
    def __init__(self):
        self.b_arg_list=list(self.__dict__.keys())
        self.b_arg_list.remove('behaviorName')
        self.b_arg_list.sort()
        self.b_arg_parameters = UniqueList()
        
    def init(self):
        self.b_arg={}
        self.fsm=FSM('UnInited',[])
        self.gliderState=None
        self.b_arg['resume']=Flag(False)
        self.b_arg['running']=Flag(True)
        self.b_arg['timeout']=Flag(False)

    def get_current_state(self):
        return self.fsm.current_state

    def resume(self,fsm):
        self.b_arg['resume'].set_False()
        fsm.memory=[]
        self.Initialise()

    def Initialise(self):
        pass
    def UnInited(self,fsm):
        print("In UnInited")

    def Active(self,fsm):
        print("In Active")
        self.updateMS(INPROGRESS)

    def Complete(self,fsm):
        print("In complete")
        self.updateMS(COMPLETED)

    def Abort(self,fsm):
        print("In Abort: ", fsm.input_symbol)
        self.updateMS(ABORTS[fsm.input_symbol])

    def process(self,gs):
        self.gliderState=gs
        CLRS.r(self.behaviorName+" "+str(self.fsm.current_state))
        CLRS.w("Checking conditions:")
        for arg,c in self.b_arg.items():
            if c.check(gs):
                self.fsm.process(arg)

        #print("behaviors:process(): time:",  self.gliderState['m_present_time'])
        #input("\nPress return")
        
    def updateMS(self,ms):
        Behavior.MS+= ~Behavior.MS&ms # x+=~x&2 add 2 if x&2 is 0, 0 otherwise.
        CLRS.b("Mission Status: %s"%(Behavior.MS))

    def printInfo(self):
        CLRS.y(f"Behavior: {self.behaviorName}")
        for i in self.b_arg_list:
            CLRS.y("%s: %s "%(i,eval("self.%s"%(i))))
        CLRS.y("")

    def get_parameter_settings(self):
        d = OrderedDict()
        for k in self.b_arg_parameters:
           d[k] = self.__dict__[k]
        return d

    def get_mafile_name(self):
        try:
            if self.args_from_file>=0:
                s = f"{self.behaviorName[:6].lower()}{self.args_from_file:02d}.ma"
        except AttributeError:
            s =''
        return s

class WhenBehavior(Behavior):
    def __init__(self,
                 start_when,
                 when_secs,
                 when_wpt_dist):
        self.start_when=start_when
        self.when_secs=when_secs
        self.when_wpt_dist=when_wpt_dist
        Behavior.__init__(self)
        self.b_arg_parameters+='start_when when_secs when_wpt_dist'.split()
        
    def init(self):
        Behavior.init(self)
        if self.start_when==0: # immediately
            #self.b_arg['start_when']=Condition('m_present_time','>',0,(None,None))
            self.b_arg['start_when']=Flag(True)
        elif self.start_when==1: # stack idle
            self.b_arg['start_when']=Condition('stack','==',0,(None,None))
        elif self.start_when==2: # pitch idle
            self.b_arg['start_when']=Condition('pitch_stack','==',0,(None,None))
        elif self.start_when==3: # heading idle
            self.b_arg['start_when']=Condition('fin_stack','==',0,(None,None))
        elif self.start_when==4: # bpump idle
            self.b_arg['start_when']=Condition('bpump_stack','==',0,(None,None))
        elif self.start_when==7: # close to waypoint
            self.b_arg['start_when']=Condition('m_dist_to_wpt','<',self.when_wpt_dist,(0,None))
        elif self.start_when==9: # Time since cycle start
            self.b_arg['start_when']=Condition('time_since_cycle_start','>',self.when_secs,(0,None))
        elif self.start_when==12: # No comms
            self.b_arg['start_when']=Condition('nocomms','>',self.when_secs,(0,None))
        elif self.start_when==13: # at UTC
            self.b_arg['start_when']=UTC_Condition((self.when_utc_min,
                                                    self.when_utc_hour,
                                                    self.when_utc_day,
                                                    self.when_utc_month))
        else:
            raise ValueError('start_when=%d is not implemented!'%(self.start_when))
        

class DiveClimbBehavior(WhenBehavior):
    def __init__(self,
                 target_depth,
                 target_altitude,
                 use_bpump,
                 bpump_value,
                 use_pitch,
                 pitch_value,
                 start_when,
                 stop_when_hover_for,
                 stop_when_stalled_for):
        self.target_depth=target_depth
        self.target_altitude=target_altitude
        self.use_bpump=use_bpump 
        self.bpump_value=bpump_value
        self.use_pitch=use_pitch         
        self.pitch_value=pitch_value
        self.start_when=start_when           
        self.stop_when_hover_for=stop_when_hover_for  
        self.stop_when_stalled_for=stop_when_stalled_for
        WhenBehavior.__init__(self,self.start_when,when_secs=None,when_wpt_dist=None)
        self.b_arg_parameters+='target_depth target_altitude use_bpump bpump_value use_pitch pitch_value start_when stop_when_hover_for stop_when_stalled_for'.split()
        
    def init(self):
        WhenBehavior.init(self)
        self.diveclimb=UpDownSettings(self.use_bpump,self.bpump_value,self.use_pitch,self.pitch_value)
        # condition when to stop
        self.b_arg['stop_when']=Condition('m_altitude','<',self.target_altitude,(0,None),
                                          'hover_for','>',self.stop_when_hover_for,(0,None),
                                          'stalled_for','>',self.stop_when_stalled_for,(0,None))
        # activate when start_when:
        self.fsm.add_transition('start_when','UnInited',self.Active,'Active')
        self.fsm.add_transition('stop_when','Active',self.Complete,'Complete')
        self.fsm.add_transition('resume','Complete',self.resume,'UnInited')
        # if nothing applies, stay where you are
        self.fsm.add_transition_any('Complete',action=None,next_state=None)
        self.fsm.add_transition_any('UnInited',action=None,next_state=None)
        self.fsm.add_transition_any('Active',action=None,next_state=None)
        self.fsm.add_transition_any('Abort',None,None)

    def Active(self,fsm):
        # when we are here, we can set start_when to False
        self.b_arg['start_when'].set_False()
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        fsm.memory.append(self.diveclimb.get_ballast_pumped())
        fsm.memory.append(self.diveclimb.get_pitch())

    def Complete(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        # when we are here, we can set start_when to True if needed for a next time
        self.b_arg['start_when'].set_True()
        fsm.memory=[]
        #reset any timers
        self.gliderState['hover_for']=0.
        self.gliderState['stalled_for']=0
        self.gliderState['samedepth_for']=0.

############### Helper classes ################

class UpDownSettings(object):
    def __init__(self,
                 use_bpump,bpump_value,
                 use_pitch,pitch_value):
        self.use_bpump=use_bpump
        self.bpump_value=bpump_value
        self.use_pitch=use_pitch
        self.pitch_value=pitch_value
        
    def get_ballast_pumped(self):
        if self.use_bpump!=2:
            raise ValueError("Only use_bpump==2 implemented. Sorry.")
        return 'c_ballast_pumped',self.bpump_value # irrespective of use_bpump.

    def get_pitch(self):
        if self.use_pitch==3:
            return 'c_pitch',self.pitch_value 
        elif self.use_pitch==1:
            return 'c_battpos',self.pitch_value 
        else:
            raise ValueError("Only use_pitch==3 implemented. Sorry. Perhaps disable error message?")
########## Official Behaviors #################
        
class Abend(Behavior):
    def __init__(self,
                 overdepth=-1,
                 overtime=-1,
                 samedepth_for=-1
                 ):
        self.overdepth=overdepth    
        self.overtime=overtime     
        self.samedepth_for=samedepth_for
        self.behaviorName='Abend'
        Behavior.__init__(self)
        self.b_arg_parameters+='overdepth overtime samedepth_for'.split()
        
    def init(self):
        Behavior.init(self)
        # set defaults
        self.b_arg['overdepth']=Condition('m_depth','>',self.overdepth,(0,None))
        self.b_arg['overtime']=Condition('m_present_secs_into_mission','>',self.overtime,(0,None))
        #self.b_arg['samedepth_for']=ConditionAnd('samedepth_for','>',self.samedepth_for,(0,None),
        #                                         'm_depth','>',0.1,(None,None))
        self.b_arg['samedepth_for']=Condition('samedepth_for','>',self.samedepth_for,(0,None))

        # add a condition to check wether or not at surface. 
        self.b_arg['at_surface']=Condition('m_depth','<',0.1,(None,None))
        # activate immediately
        self.fsm.add_transition_any('UnInited',self.Active,'Active')
        
        # add transistions for b_arg:
        abortKeys=list(self.b_arg.keys())
        abortKeys.remove('at_surface') # this should not trigger abort
        abortKeys.remove('running') # this should not trigger abort
        for i in abortKeys:
            self.fsm.add_transition(i,'Active',self.Abort,'Abort')
        
        # if nothing applies, stay where you are
        # if at surface and in Abort mode -> Completed.
        self.fsm.add_transition('at_surface','Abort',self.Complete,'Complete')
        self.fsm.add_transition_any('Active',None,None)
        self.fsm.add_transition_any('Abort',None,None)
        self.fsm.add_transition_any('Complete',None,None)
        #
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)
    
    def Active(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
            
    def Complete(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)

class Surface(WhenBehavior):
    def __init__(self,
                 start_when=0,
                 when_secs=180,
                 when_wpt_dist=10,
                 end_action=1,
                 end_wpt_dist=0,
                 c_use_bpump=2,
                 c_bpump_value=200,
                 c_use_pitch=3,
                 c_pitch_value=0.4363,
                 keystroke_wait_time=30,
                 gps_wait_time=30,
                 datatransfertime=0.):
        self.start_when = start_when         
        self.when_secs = when_secs          
        self.when_wpt_dist = when_wpt_dist      
        self.end_action = end_action         
        self.end_wpt_dist = end_wpt_dist       
        self.c_use_bpump = c_use_bpump        
        self.c_bpump_value = c_bpump_value      
        self.c_use_pitch = c_use_pitch        
        self.c_pitch_value = c_pitch_value      
        self.keystroke_wait_time = keystroke_wait_time
        self.datatransfertime=datatransfertime
        self.gps_wait_time = gps_wait_time
        self.behaviorName='Surface'
        WhenBehavior.__init__(self,self.start_when,self.when_secs,self.when_wpt_dist)
        self.b_arg_parameters+='end_action end_wpt_dist c_use_bpump c_bpump_value c_use_pitch c_pitch_value keystroke_wait_time'.split()


    def init(self):
        #WhenBehavior.__init__(self,self.start_when,self.when_secs,self.when_wpt_dist)
        WhenBehavior.init(self)
        self.climb=UpDownSettings(self.c_use_bpump,self.c_bpump_value,self.c_use_pitch,self.c_pitch_value)
        
        # condition when to stop
        self.b_arg['stop_when']=Condition('m_depth','<',0.01,(None,None))
        # activate when start_when:
        self.fsm.add_transition('start_when','UnInited',self.Active,'Active')
        self.fsm.add_transition('stop_when','Active',self.Complete,'Complete')
        self.fsm.add_transition('resume','Complete',self.WaitForGPS,'WaitForGPS')
        self.fsm.add_transition('resume','WaitForGPS',action=None,next_state='WaitForUser')
        self.fsm.add_transition('resume','WaitForUser',
                                self.WaitForFinalGPS,'WaitForFinalGPS')
        self.fsm.add_transition('resume','WaitForFinalGPS',self.getBusy,'Busy')
        self.fsm.add_transition('resume','Busy',self.resume,'UnInited')
        # if nothing applies, stay where you are
        self.fsm.add_transition_any('UnInited',action=None,next_state=None)
        self.fsm.add_transition_any('Active',action=None,next_state=None)
        self.fsm.add_transition_any('Abort',None,None)
        self.fsm.add_transition_any('Complete',None,None)
        self.fsm.add_transition_any('WaitForGPS',self.WaitForGPS,None)
        self.fsm.add_transition_any('WaitForUser',self.WaitForUser,None)
        self.fsm.add_transition_any('WaitForFinalGPS',self.WaitForFinalGPS,None)
        self.fsm.add_transition_any('Busy',self.beBusy,None)
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)

    def Active(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        fsm.memory.append(self.climb.get_ballast_pumped())
        fsm.memory.append(self.climb.get_pitch())
        # switch on gps
        self.gliderState['c_gps_on']=1

    def Complete(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        fsm.memory.append(('c_ballast_pumped',1000))
        fsm.memory.append(('c_battpos',1000))
        self.surfacingTime=self.gliderState['m_present_time']
        self.DRsurfacingLmc=(self.gliderState['m_lmc_x'],
                             self.gliderState['m_lmc_y']) # dead reckoned
        if self.end_action>0: #resume
            self.b_arg['resume'].set_True()
        else:
            self.updateMS(TOQUIT)
        # if come up because of nocomms, reset nocomms
        if self.start_when==12:
            self.gliderState['nocomms']=0.
        # frome here, we start a new cylce:
        self.gliderState['time_since_cycle_start']=0
        # reset hovering variables too
        self.gliderState['hover_for']=0.
        self.gliderState['stalled_for']=0
        self.gliderState['samedepth_for']=0.
        #
        self.gliderState['m_segment_number']+=1

    def WaitForGPS(self,fsm):
        self.b_arg['resume'].set_False()
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        currentTime=self.gliderState['m_present_time']
        self.gliderState['nocomms']=0.
        # reset hovering variables too
        self.gliderState['hover_for']=0.
        self.gliderState['stalled_for']=0.
        self.gliderState['samedepth_for']=0.
        # leave this state if:
        if self.gliderState['m_gps_status']==0 or \
                currentTime-self.surfacingTime>self.gps_wait_time:
            self.b_arg['resume'].set_True()
            if self.gliderState['m_gps_status']==0: # good fix:
                self.surfacingLmc=(self.gliderState['m_lmc_y'])
                dx=self.gliderState['m_lmc_x']-self.DRsurfacingLmc[0]
                dy=self.gliderState['m_lmc_y']-self.DRsurfacingLmc[1]
                dt=self.surfacingTime-self.gliderState['x_time_dive']
                if dt==0:
                    self.gliderState['m_water_vx']=-1.
                    self.gliderState['m_water_vy']=-1.
                else:
                    self.gliderState['m_water_vx']=dx/dt
                    self.gliderState['m_water_vy']=dy/dt
            else:
                self.gliderState['m_water_vx']=-1.
                self.gliderState['m_water_vy']=-1.
        CLRS.w("Time at surface: %f"%(currentTime-self.surfacingTime))
        CLRS.w("gps status: %f"%(self.gliderState['m_gps_status']))

        
    def WaitForUser(self,fsm):
        self.b_arg['resume'].set_False()
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        currentTime=self.gliderState['m_present_time']
        self.gliderState['nocomms']=0.
        # reset hovering variables too
        self.gliderState['hover_for']=0.
        self.gliderState['stalled_for']=0.
        self.gliderState['samedepth_for']=0.
        if self.end_action==2: #resume
            self.b_arg['resume'].set_True()
            self.gliderState['c_gps_on']=0 # switch off gps
        elif self.end_action==1: # wait for ctrl-c
            surfaceTime=currentTime-self.surfacingTime
            if surfaceTime>self.datatransfertime and surfaceTime>self.keystroke_wait_time:
                self.b_arg['resume'].set_True()
                self.gliderState['c_gps_on']=0 # switch off gps
        else: # end
            self.b_arg['resume'].set_True()
        CLRS.w("Time at surface: %f"%(currentTime-self.surfacingTime))

    def WaitForFinalGPS(self,fsm):
        self.b_arg['resume'].set_False()
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        currentTime=self.gliderState['m_present_time']
        self.gliderState['nocomms']=0.
        # reset hovering variables too
        self.gliderState['hover_for']=0.
        self.gliderState['stalled_for']=0.
        self.gliderState['samedepth_for']=0.
        # leave this state if:
        if self.gliderState['m_gps_status']==0 or \
                currentTime-self.surfacingTime>self.gps_wait_time:
            if self.gliderState['m_gps_status']==0: # good fix:
                self.gliderState['x_gps_lmc_x_dive']=self.gliderState['m_lmc_x']
                self.gliderState['x_gps_lmc_y_dive']=self.gliderState['m_lmc_y']
                self.gliderState['x_lmc_x_wpt_calc']=self.gliderState['m_lmc_x']
                self.gliderState['x_lmc_y_wpt_calc']=self.gliderState['m_lmc_y']
                self.gliderState['x_time_dive']=self.gliderState['m_present_time']
            self.b_arg['resume'].set_True()
            # This seems not to make much sense really...
            #if self.start_when==13: # triggered by UTC time:
            #    self.b_arg['start_when'].set_False()

    def getBusy(self,fsm):
        self.b_arg['resume'].set_False()
        self.__busytime=self.gliderState['m_present_time']
    
    def beBusy(self,fsm):
        # keep my self busy until init_dive_time is exceeded.
        if (self.gliderState['m_present_time']-self.__busytime)> \
                self.gliderState['_init_dive_time']:
            self.b_arg['resume'].set_True()

            
class Dive_to(DiveClimbBehavior):
    def __init__(self,
                 target_depth=10,
                 target_altitude=-1,
                 use_bpump=2,
                 bpump_value=-233,
                 use_pitch=1,
                 pitch_value=0,
                 start_when=0,
                 stop_when_hover_for=180,
                 stop_when_stalled_for=240):
        self.target_depth=target_depth         
        self.target_altitude=target_altitude      
        self.use_bpump=use_bpump            
        self.bpump_value=bpump_value          
        self.use_pitch=use_pitch            
        self.pitch_value=pitch_value          
        self.start_when=start_when           
        self.stop_when_hover_for=stop_when_hover_for  
        self.stop_when_stalled_for=stop_when_stalled_for
        self.behaviorName='Dive_to'
        DiveClimbBehavior.__init__(self, self.target_depth,self.target_altitude,self.use_bpump,
                                   self.bpump_value,self.use_pitch,self.pitch_value,self.start_when,
                                   self.stop_when_hover_for,self.stop_when_stalled_for)
        self.b_arg_parameters+='target_depth target_altitude use_bpump bpump_value use_pitch pitch_value start_when stop_when_hover_for stop_when_stalled_for'.split()
        
    def init(self):
        DiveClimbBehavior.init(self)
        # condition when to stop
        self.b_arg['stop_when'].addCondition('m_depth','>',self.target_depth,(0,None))
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)
        #CLRS.b("target_depth %f"%(self.target_depth))
        
class Climb_to(DiveClimbBehavior):
    def __init__(self,
                 target_depth=10,
                 target_altitude=-1,
                 use_bpump=2,
                 bpump_value=-233,
                 use_pitch=1,
                 pitch_value=0,
                 start_when=0,
                 stop_when_hover_for=180,
                 stop_when_stalled_for=240):
        self.target_depth=target_depth         
        self.target_altitude=target_altitude      
        self.use_bpump=use_bpump            
        self.bpump_value=bpump_value          
        self.use_pitch=use_pitch            
        self.pitch_value=pitch_value          
        self.start_when=start_when           
        self.stop_when_hover_for=stop_when_hover_for  
        self.stop_when_stalled_for=stop_when_stalled_for
        self.behaviorName='Climb_to'
        DiveClimbBehavior.__init__(self, self.target_depth,self.target_altitude,self.use_bpump,
                                   self.bpump_value,self.use_pitch,self.pitch_value,self.start_when,
                                   self.stop_when_hover_for,self.stop_when_stalled_for)

    def init(self):
        DiveClimbBehavior.init(self)
        # condition when to stop
        self.b_arg['stop_when'].addCondition('m_depth','<',self.target_depth,(0,None))
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)

class Set_heading(WhenBehavior):
    def __init__(self,
                 start_when=0,
                 stop_when=0,
                 when_secs=1200,
                 heading_value=1000,
                 use_heading=2):
        self.start_when=start_when
        self.stop_when=stop_when
        self.when_secs=when_secs
        self.heading_value=heading_value
        self.use_heading=use_heading
        self.behaviorName='Set_heading'
        WhenBehavior.__init__(self,self.start_when,self.when_secs,0)
        self.b_arg_parameters+='heading_value use_heading'.split()
            
    def init(self):
        WhenBehavior.init(self)
        if self.stop_when==0 or self.stop_when==5:
            self.b_arg['stop_when']=Flag(False)
        else:
            raise ValueError('Value for stop_when not impemented')

        self.fsm.add_transition('start_when','UnInited',self.Active,'Active')
        self.fsm.add_transition('stop_when','Active',self.Complete,'Complete')
        # if nothing applies, stay where you are
        self.fsm.add_transition_any('UnInited',action=None,next_state=None)
        self.fsm.add_transition_any('Active',action=None,next_state=None)
        self.fsm.add_transition_any('Complete',None,None)
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)
        
    def Active(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)

        # set values for the initial parameters
        m_lat=self.gliderState['m_lat']
        m_lon=self.gliderState['m_lon']
        self.position0=latlon.LatLon(m_lat,m_lon,format='nmea')
        self.gliderState['m_lmc_x']=0.
        self.gliderState['m_lmc_y']=0.
        self.gliderState['utm_0']=self.position0.UTM()


        if self.use_heading==2:
            fsm.memory.append(('c_heading',self.heading_value))
        elif self.use_heading==4:
            fsm.memory.append(('c_fin',self.heading_value))
        else:
            raise ValueError('Unimplemented value for "use_heading" in "Set_heading" behavior')
    def Complete(self,fsm):
        # dont think we'll ever get here...
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        fsm.memory=[]
        self.b_arg['stop_when']=Flag(True)

class Yo(WhenBehavior):
    def __init__(self,
                 start_when=0,
                 num_half_cycles_to_do=2,
                 d_target_depth=10,
                 d_target_altitude=-1,
                 d_use_bpump=2,
                 d_bpump_value=-200,
                 d_use_pitch=3,
                 d_pitch_value=-0.4363,
                 d_stop_when_hover_for=180,
                 d_stop_when_stalled_for=240,
                 c_target_depth=3,
                 c_target_altitude=-1,
                 c_use_bpump=2,
                 c_bpump_value=200,
                 c_use_pitch=3,
                 c_pitch_value=0.4363,
                 c_stop_when_hover_for=180,
                 c_stop_when_stalled_for=240,
                 end_action=0,
                 ):
        self.start_when=start_when               
        self.num_half_cycles_to_do=num_half_cycles_to_do    
        self.d_target_depth=d_target_depth           
        self.d_target_altitude=d_target_altitude        
        self.d_use_bpump=d_use_bpump              
        self.d_bpump_value=d_bpump_value            
        self.d_use_pitch=d_use_pitch              
        self.d_pitch_value=d_pitch_value            
        self.d_stop_when_hover_for=d_stop_when_hover_for    
        self.d_stop_when_stalled_for=d_stop_when_stalled_for  
        self.c_target_depth=c_target_depth           
        self.c_target_altitude=c_target_altitude        
        self.c_use_bpump=c_use_bpump              
        self.c_bpump_value=c_bpump_value            
        self.c_use_pitch=c_use_pitch              
        self.c_pitch_value=c_pitch_value            
        self.c_stop_when_hover_for=c_stop_when_hover_for    
        self.c_stop_when_stalled_for=c_stop_when_stalled_for  
        self.end_action=end_action                      
        self.behaviorName='Yo'
        WhenBehavior.__init__(self,self.start_when,when_secs=None,when_wpt_dist=None) #<---
        self.b_arg_parameters+='num_half_cycles_to_do d_target_altitude d_target_depth d_use_bpump d_use_pitch d_bpump_value d_pitch_value d_stop_when_hover_for d_stop_when_stalled_for'.split()
        self.b_arg_parameters+='c_target_altitude c_target_depth c_use_bpump c_use_pitch c_bpump_value c_pitch_value c_stop_when_hover_for c_stop_when_stalled_for end_action'.split()
        

    def init(self):
        WhenBehavior.init(self)                                                      #needs
                                                                                 #change
                                                                                 #for
                                                                                 #other
                                                                                 #when
                                                                                 #actions

        # activate when start_when:
        self.fsm.add_transition('start_when','UnInited',self.Active,'Active')
        self.fsm.add_transition('stop_when','Active',self.Complete,'Complete')
        self.fsm.add_transition('start_when','Active',action=self.SubState,next_state='Active')
        self.fsm.add_transition('resume','Complete',self.resume,'UnInited')
        # if nothing applies, stay where you are
        self.fsm.add_transition_any('UnInited',action=None,next_state=None)
        self.fsm.add_transition_any('Complete',action=None,next_state=None)
        self.fsm.add_transition_any('Active',action=self.SubState,next_state='Active')
        #
        self.Initialise()
    
    def Initialise(self):
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)#+"->"+fsm.next_state)
        self.current_profile=-1
        # reset some values for m_speed calcualtion
        divestate=Dive_to(target_depth=self.d_target_depth,
                          target_altitude=self.d_target_altitude,
                          use_bpump=self.d_use_bpump,
                          bpump_value=self.d_bpump_value,
                          use_pitch=self.d_use_pitch,
                          pitch_value=self.d_pitch_value,
                          stop_when_hover_for=self.d_stop_when_hover_for,
                          stop_when_stalled_for=self.d_stop_when_stalled_for)
        divestate.init()
        climbstate=Climb_to(target_depth=self.c_target_depth,
                            target_altitude=self.c_target_altitude,
                            use_bpump=self.c_use_bpump,
                            bpump_value=self.c_bpump_value,
                            use_pitch=self.c_use_pitch,
                            pitch_value=self.c_pitch_value,
                            stop_when_hover_for=self.c_stop_when_hover_for,
                            stop_when_stalled_for=self.c_stop_when_stalled_for)
        climbstate.init()
        self.substates=[divestate,climbstate]
        # condition when to stop
        self.b_arg['stop_when']=Flag(False)
        
    def Active(self,fsm):
        # reset the values of cycle in dex and m_speed for the kalman filter approach 
        # to a running average.
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        self.current_profile+=1
        CLRS.b("Current profile: %0d"%(self.current_profile))
        self.SubState(fsm)


    def Complete(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        fsm.memory=[]
        if self.end_action==2: #resume
            self.b_arg['resume'].set_True()
        elif self.end_action==0:
            self.updateMS(TOQUIT)
        self.gliderState['hover_for']=0.
        self.gliderState['stalled_for']=0
        self.gliderState['samedepth_for']=0.
    
    def SubState(self,fsm):
        CLRS.g(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        substate=self.substates[self.current_profile%2]
        substate.process(self.gliderState)
        if substate.fsm.current_state=='Complete':
            substate.b_arg['resume'].set_True()
            substate.b_arg['stop_when'].set_False()
            substate.b_arg['start_when'].set_False()
            substate.process(self.gliderState)


            if self.current_profile==self.num_half_cycles_to_do-1:
                self.b_arg['stop_when'].set_True()
            else:
                self.current_profile+=1
                substate=self.substates[self.current_profile%2]
                substate.b_arg['start_when'].set_True()
        else:
            CLRS.b("Current profile: %0d"%(self.current_profile))
            # pass memory on
            fsm.memory=list(substate.fsm.memory)



class SGYo(Yo):
    ''' subclassed Yo behavior to mimick the seaglider behaviour.'''
    def __init__(self,
                 d_target_depth=10,
                 target_divetime=1200,
                 bpump_offset=0.,
                 d_pitch_value=0.3,
                 drag_coefficient=0.095
                 ):
        Yo.__init__(self,
                    # "hard coded values"
                    start_when=2,
                    num_half_cycles_to_do=2,
                    d_target_altitude=10,
                    d_use_bpump=2,
                    d_use_pitch=3,
                    d_stop_when_hover_for=600,
                    d_stop_when_stalled_for=600,
                    c_target_altitude=-1,
                    c_target_depth=3,
                    c_use_bpump=2,
                    c_use_pitch=3,
                    c_stop_when_hover_for=600,
                    c_stop_when_stalled_for=600,
                    end_action=2)
        self.d_target_depth=d_target_depth
        self.target_divetime=target_divetime
        self.bpump_offset=bpump_offset
        self.d_pitch_value=d_pitch_value
        self.drag_coefficient=drag_coefficient
        self.behaviorName='SGYo'
        WhenBehavior.__init__(self,self.start_when,when_secs=None,when_wpt_dist=None) #<---

    def init(self):
        WhenBehavior.init(self)                                                      #needs
                                                                                 #change
                                                                                 #for
                                                                                 #other
                                                                                 #when
                                                                                 #actions

        # activate when start_when:
        self.fsm.add_transition('start_when','UnInited',self.Active,'Active')
        self.fsm.add_transition('stop_when','Active',self.Complete,'Complete')
        self.fsm.add_transition('start_when','Active',action=self.SubState,next_state='Active')
        self.fsm.add_transition('resume','Complete',self.resume,'UnInited')
        # if nothing applies, stay where you are
        self.fsm.add_transition_any('UnInited',action=None,next_state=None)
        self.fsm.add_transition_any('Complete',action=None,next_state=None)
        self.fsm.add_transition_any('Active',action=self.SubState,next_state='Active')
        #
        self.c_pitch_value=abs(self.d_pitch_value)
        self.d_pitch_value=-abs(self.d_pitch_value) # just to make sure...
        self.d_bpump_value,self.c_bpump_value=self.compute_buoyancy_values(self.d_target_depth,
                                                                           self.target_divetime,
                                                                           self.bpump_offset,
                                                                           self.c_pitch_value)

        self.Initialise()

    def compute_buoyancy_values(self,d_target_depth,target_divetime, bpump_offset,c_pitch_value):
        S=0.12
        Cd=self.drag_coefficient
        g=9.81
        DV=0.5*Cd*S
        DV*=(2.*d_target_depth/target_divetime/sin(c_pitch_value))**2
        DV/=g*sin(c_pitch_value)
        DV*=1e6 # to get to cc
        c_bpump_value=DV+bpump_offset
        d_bpump_value=-DV+bpump_offset
        return d_bpump_value,c_bpump_value
        



class Goto_list(WhenBehavior):
    def __init__(self,
                 start_when=0,
                 num_waypoints=0,
                 num_legs_to_run=0,
                 initial_wpt=0,
                 list_stop_when=7,
                 list_when_wpt_dist=10,
                 waypoints=None):
        self.start_when=start_when               
        self.num_waypoints=num_waypoints            
        self.num_legs_to_run=num_legs_to_run          
        self.initial_wpt=initial_wpt              
        self.list_stop_when=list_stop_when           
        self.list_when_wpt_dist=list_when_wpt_dist       
        if waypoints:
            self.waypoints=waypoints                
        else:
            self.waypoints=list()
        self.activated_waypoints=[]
        self.behaviorName='Goto_list'
        WhenBehavior.__init__(self,self.start_when,when_secs=None,when_wpt_dist=None) #<---
        self.b_arg_parameters+='num_waypoints num_legs_to_run initial_wpt list_stop_when list_when_wpt_dist waypoints'.split()

    def init(self):
        WhenBehavior.init(self)                                                  #needs
                                                                                 #change
                                                                                 #for
                                                                                 #other
                                                                                 #when
                                                                                 #actions
        #
        self.b_arg['stop_when']=Flag(False)
        self.b_arg['wpt_reached']=Flag(False)
        # activate when start_when:
        #self.fsm.add_transition('start_when','UnInited',self.TranslatingWaypoints,'TranslatingWaypoints')
        #self.fsm.add_transition('start_when','TranslatingWaypoints',self.Active,'Active')
        self.fsm.add_transition('start_when','UnInited',self.Active,'Active')
        self.fsm.add_transition('stop_when','Active',self.Complete,'Complete')
        self.fsm.add_transition('resume','Complete',self.resume,'Uninited')
        # if nothing applies, stay where you are
        self.fsm.add_transition_any('UnInited',action=None,next_state=None)
        self.fsm.add_transition_any('Complete',action=None,next_state=None)
        self.fsm.add_transition_any('Active',action=self.Steering,next_state='Active')
        #
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)

    def TranslatingWaypoints(self,fsm):
        # translate waypoints
        self.activeWaypoint=None
        self.achievedWaypoints=0
        # first get current position.
        m_lat=self.gliderState['m_lat']
        m_lon=self.gliderState['m_lon']
        self.position0=latlon.LatLon(m_lat,m_lon,format='nmea')
        self.gliderState['m_lmc_x']=0.
        self.gliderState['m_lmc_y']=0.
        self.gliderState['utm_0']=self.position0.UTM()
        CLRS.b("Translating waypoints to lmc...")
        self.wpt_lmc=[]
        for i in range(self.num_waypoints):
            p=latlon.LatLon(self.waypoints[i][1],self.waypoints[i][0],format='nmea')
            dist=self.position0.distance(p)
            self.wpt_lmc.append((self.position0.dx,self.position0.dy,dist))
            tmp=self.wpt_lmc[-1]
            CLRS.w("Waypoint %d %f %f (dist: %f)"%(i,tmp[0],tmp[1],tmp[2]))

    def Active(self,fsm):
        CLRS.g(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        self.TranslatingWaypoints(fsm)
        r=self.__getInitialWaypoint()
        fsm.memory=[('c_wpt_latlon',self.setWaypoint(r))]

    def Steering(self,fsm):
        CLRS.g(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        # set distance to waypoint
        x0=self.gliderState['m_lmc_x']
        y0=self.gliderState['m_lmc_y']
        r=self.activeWaypoint
        x1=self.wpt_lmc[r][0]
        y1=self.wpt_lmc[r][1]
        dist=sqrt((x0-x1)**2+(y0-y1)**2)
        self.gliderState['m_dist_to_wpt']=dist
        CLRS.w("distance to waypoint: %f"%(dist))
        #print(dist, self.gliderState['c_heading'], self.gliderState['c_wpt_lat'], self.gliderState['c_wpt_lon'])
        if self.list_stop_when==7 and dist<=self.list_when_wpt_dist:
            self.achievedWaypoints+=1
            self.gliderState['x_last_wpt_lat']=self.waypoints[r][1]
            self.gliderState['x_last_wpt_lon']=self.waypoints[r][0]
            self.gliderState['x_lmc_x_wpt_calc']=self.gliderState['m_lmc_x']
            self.gliderState['x_lmc_y_wpt_calc']=self.gliderState['m_lmc_y']
            if self.num_legs_to_run==self.achievedWaypoints:
                self.b_arg['stop_when'].set_True()
            elif self.num_legs_to_run==-2 and self.achievedWaypoints==self.num_waypoints:
                self.b_arg['stop_when'].set_True()
            elif self.num_legs_to_run==-1 or self.num_legs_to_run>0 or self.num_legs_to_run==-2:
                CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
                self.activeWaypoint+=1
                self.activeWaypoint%=(self.num_waypoints)
                r=self.activeWaypoint
                fsm.memory=[('c_wpt_latlon',self.setWaypoint(r))]
            else:
                raise ValueError('Illegal option in goto_list for num_legs_to_run.')

    def Complete(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        fsm.memory=[]
        self.updateMS(TOQUIT)

    def __getClosestWaypoint(self):
        mindist=1e9
        r=None
        for i,v in enumerate(self.wpt_lmc):
            if v[2]<mindist:
                r=i
                mindist=v[2]
        if r!=None:
            return r
        else:
            raise ValueError('Could not find closest waypoint')

    def __getWaypointAfterLastAchieved(self):
        last_wpt_lat=self.gliderState['x_last_wpt_lat']
        last_wpt_lon=self.gliderState['x_last_wpt_lon']
        found=-1
        CLRS.b("last achieved lat/lon",last_wpt_lat,last_wpt_lon)
        CLRS.b("Waypoint list:")
        for i,(lon,lat) in enumerate(self.waypoints):
            CLRS.b(i,lat,lon)
        for i,(lon,lat) in enumerate(self.waypoints):
            if abs(lon-last_wpt_lon)<1e-4 and abs(lat-last_wpt_lat)<1e-4:
                found=i
                CLRS.b("Waypoint found:", "(%d)"%(i),lat,lon)
                break
        if found!=-1:
            # last achieved waypoint in the list
            n_waypoints=len(self.waypoints)
            r=(found+1)%n_waypoints
        else:
            r=0
        return r

    def __getWaypointForPickup(self):
        # waypoint is already prescribed as we continue a running mission
        self.gliderState['_pickup']=False # so we don't do it again.
        c_wpt_lat=self.gliderState['c_wpt_lat']
        c_wpt_lon=self.gliderState['c_wpt_lon']
        found=-1
        logger.info(f"Preset waypoint lat: {c_wpt_lat:6.3f}, lon: {c_wpt_lon:6.3f}")
        logger.info("Waypoint list:")
        for i,(lon,lat) in enumerate(self.waypoints):
            logger.info(f"#{i}: {lat:6.3f}, {lon:6.3f}")
        for i,(lon,lat) in enumerate(self.waypoints):
            if abs(lon-c_wpt_lon)<1e-4 and abs(lat-c_wpt_lat)<1e-4:
                found=i
                logger.info(f"Waypoint found: ({i}) {lat:6.3f} {lon:6.3f}")
                break
        if found==-1:
            # should not happen, then something went wrong.
            logger.warning("Preset waypoint is not found in the waypoint list, assuming new mission start.")
            logger.warning(f"Waypoint: {self.waypoints[0][0]:6.3f}, {self.waypoints[0][1]:6.3f}")
            found=0
        return found
        
        
    def __getInitialWaypoint(self):
        if self.gliderState['_pickup']:
            # set r to the corresponding waypoint in the list. We're picking up a running mission
            r=self.__getWaypointForPickup()
        elif self.initial_wpt>=0 and self.initial_wpt<self.num_waypoints:
            r=self.initial_wpt
        elif self.initial_wpt==-1:
            r=self.__getWaypointAfterLastAchieved()
        elif self.initial_wpt==-2:
            r=self.__getClosestWaypoint()
        else:
            raise ValueError("Could not find current waypoint!")
        return r

    def setWaypoint(self,r):
        self.gliderState['c_wpt_lat']=self.waypoints[r][1]
        self.gliderState['c_wpt_lon']=self.waypoints[r][0]
        self.gliderState['c_wpt_lmc_x']=self.wpt_lmc[r][0]
        self.gliderState['c_wpt_lmc_y']=self.wpt_lmc[r][1]
        CLRS.b("Setting waypoint to:")
        CLRS.b("%f %f (%f %f)"%(self.gliderState['c_wpt_lat'],
                                self.gliderState['c_wpt_lon'],
                                self.gliderState['c_wpt_lmc_x'],
                                self.gliderState['c_wpt_lmc_y']))
        CLRS.b("New waypoint: %f %f. Mission time (hr): %.2f"%(self.gliderState['c_wpt_lat'],
                                                               self.gliderState['c_wpt_lon'],
                                                               self.gliderState['m_present_secs_into_mission']/3600))
        self.activeWaypoint=r
        self.activated_waypoints.append((self.gliderState['m_present_time'],
                                         self.waypoints[r]))
        return self.wpt_lmc[r][0],self.wpt_lmc[r][1]


class Prepare_to_dive(WhenBehavior):
    def __init__(self,
                 start_when=0,
                 wait_time=720,):
        self.start_when=start_when
        self.wait_time=wait_time
        self.behaviorName='Prepare_to_dive'
        WhenBehavior.__init__(self,self.start_when,None,None)
        self.b_arg_parameters+=['wait_time']
        
    def init(self):
        WhenBehavior.init(self)
        self.t0=None
        self.b_arg['stop_when']=Flag(False)
        self.fsm.add_transition('start_when','UnInited',self.Active,'Active')
        self.fsm.add_transition_any('Active',action=self.collectGPS,next_state=None)
        self.fsm.add_transition('stop_when','Active',self.Complete,'Complete')
        # if in complete, stay here.
        self.fsm.add_transition_any('Complete',action=None,next_state=None)
        self.fsm.add_transition_any('UnInited',action=None,next_state=None)
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)
        
    def Active(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        # switch on gps
        self.gliderState['c_gps_on']=1
        self.t0=self.gliderState['m_present_time']
        # we should block all behaviours that start on an empty stack behavior.
        self.gliderState['keep_stack_busy']=1
        
    def collectGPS(self,fsm):
        if self.gliderState['m_present_time']-self.t0>=self.wait_time:
            self.b_arg['stop_when'].set_True()
        if self.gliderState['m_gps_status']==0:
            self.b_arg['stop_when'].set_True()
        # we intend to stay at the surface...
        self.gliderState['hover_for']=0.
        self.gliderState['stalled_for']=0.
        self.gliderState['samedepth_for']=0.
        
    def Complete(self,fsm):
        # set gps position at dive and relief stack
        self.gliderState['keep_stack_busy']=0
        self.gliderState['x_gps_lmc_x_dive']=self.gliderState['m_lmc_x']
        self.gliderState['x_gps_lmc_y_dive']=self.gliderState['m_lmc_y']
        self.gliderState['x_lmc_x_wpt_calc']=self.gliderState['m_lmc_x']
        self.gliderState['x_lmc_y_wpt_calc']=self.gliderState['m_lmc_y']
        self.gliderState['x_time_dive']=self.gliderState['m_present_time']

# These behaviours do actually nothing, but allow for mission files to be parsed etc.

class Sample(WhenBehavior):
    def __init__(self,
                 start_when=0):
        self.start_when=start_when
        self.behaviorName='Sample'
        self.sensor_type=0
        self.state_to_sample=1
        self.sample_time_after_state_change=15
        self.intersample_time=0
        self.nth_yo_to_sample=1
        self.intersample_depth = -1
        self.min_depth=-5
        self.max_depth=2000
        WhenBehavior.__init__(self,self.start_when,None,None)
        self.b_arg_parameters+='sensor_type state_to_sample sample_time_after_state_change intersample_time intersample_depth nth_yo_to_sample min_depth max_depth'.split()
        
    def init(self):
        WhenBehavior.init(self)
        #self.t0=None
        #self.b_arg['stop_when']=Flag(False)
        self.fsm.add_transition_any('UnInited',self.Active,'Active')
        self.fsm.add_transition_any('Active',action=None, next_state=None)
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)

    def Active(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        # We do actually nothing in this behaviour, just minimal implementation so we
        # can easily read the parameters.
        
    def Complete(self,fsm):
        pass
        
class Sensors_in(WhenBehavior):
    def __init__(self,
                 start_when=0):
        self.start_when=start_when
        self.behaviorName='Sensors_in'
        WhenBehavior.__init__(self,self.start_when,None,None)
        
    def init(self):
        WhenBehavior.init(self)
        #self.t0=None
        #self.b_arg['stop_when']=Flag(False)
        self.fsm.add_transition_any('UnInited',self.Active,'Active')
        self.fsm.add_transition_any('Active',action=None, next_state=None)
        CLRS.r(self.behaviorName+": "+self.fsm.current_state)

    def Active(self,fsm):
        CLRS.r(self.behaviorName+": "+fsm.current_state+"->"+fsm.next_state)
        # We do actually nothing in this behaviour, just minimal implementation so we
        # can easily read the parameters.
        
    def Complete(self,fsm):
        pass
