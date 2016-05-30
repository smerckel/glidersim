import re
from . import behaviors
import os

ImplementedBehaviors={'abend':behaviors.Abend,
                      'yo':behaviors.Yo,
                      'sgyo':behaviors.SGYo,
                      'dive_to':behaviors.Dive_to,
                      'climb_to':behaviors.Climb_to,
                      'goto_list':behaviors.Goto_list,
                      'surface':behaviors.Surface,
                      'prepare_to_dive':behaviors.Prepare_to_dive,
                      'set_heading':behaviors.Set_heading}

           

class MafileParser(object):
    def __init__(self,filename,behavior,mafileDirectory='mafiles'):
        self.filename=filename
        self.behavior=behavior
        self.mafileDirectory=mafileDirectory
    def parse(self):
        fp=open(os.sep.join([self.mafileDirectory,self.filename]))
        lines=fp.readlines()
        fp.close()
        # remove any leading spaces:
        lines=[i.strip() for i in lines]
        # remove any comments:
        lines=[re.sub("#.*$","",i) for i in lines]
        # remove blanks:
        lines=[i for i in lines if i]
        topline=lines.pop(0).split('=')
        if topline[0]!='behavior_name' and topline[1]!=self.behavior.behaviorName.lower():
            raise ValueError('Probably a malformed ma file. Header lines not ok')
        eolines=True
        while lines:
            line=lines.pop(0)
            if line=='<start:b_arg>':
                eolines=False
                break
        if eolines:
            raise ValueError('Probably a malformed ma file. No start:b_arg')
        eolines=True
        while lines:
            line=lines.pop(0)
            if line=='<end:b_arg>':
                eolines=False
                break
            elif line.startswith("b_arg:"):
                self.addb_arg(line)
        if eolines:
            raise ValueError('Probably a malformed ma file. No end:b_arg')
        self.lines=lines

    def addb_arg(self,i):
        dummy,param,value=i.split()
        # remove the units
        param=re.sub("\(.*\)","",param)
        try:
            valueNum=int(value)
        except ValueError:
            valueNum=float(value)
        b=self.behavior
        b.__dict__[param]=valueNum

class MafileParserWpt(MafileParser):
    def __init__(self,filename,behavior,mafileDirectory='mafiles'):
        MafileParser.__init__(self,filename,behavior,mafileDirectory)
    
    def parseWpts(self):
        lines=self.lines
        eolines=True
        while lines:
            line=lines.pop(0)
            if line=='<start:waypoints>':
                eolines=False
                break
        if eolines:
            raise ValueError('Probably a malformed ma file. No start:waypoints')
        self.behavior.waypoints=[]
        for i in range(self.behavior.num_waypoints):
            line=lines.pop(0)
            lon,lat=line.split()
            lon=float(lon)
            lat=float(lat)
            self.behavior.waypoints.append((lon,lat))
        line=lines.pop(0)
        if line!='<end:waypoints>':
            raise ValueError('Probably a malformed ma file. No end:waypoints')

class MissionParser(object):
    def __init__(self,filename,missionDirectory='missions',
                 mafileDirectory='mafiles',verbose=True):
        self.filename=filename
        self.behaviors=[]
        self.currentBehaviorName=None
        self.missionDirectory=missionDirectory
        self.mafileDirectory=mafileDirectory
        self.sensor_settings=[]
        self.verbose=verbose

    def parse(self):
        fp=open(os.sep.join([self.missionDirectory,self.filename]))
        lines=fp.readlines()
        fp.close()
        # remove any leading spaces:
        lines=[i.strip() for i in lines]
        # remove any comments:
        lines=[re.sub("#.*$","",i) for i in lines]
        # remove blanks:
        lines=[i for i in lines if i]
        read_waypoints=False # This is a hack to read waypoints in a
                             # mission file, used for seaglider
                             # simulations
        waypoint_counter=0
        for i in lines:
            if i.startswith("behavior:"):
                self.addBehavior(i)
            elif i.startswith("b_arg:"):
                self.addb_arg(i)
            elif i.startswith("sensor:"):
                self.set_sensor(i)
            elif i.startswith("<start:waypoints>"):
                read_waypoints=True
            elif i.startswith("<end:waypoints>"):
                read_waypoints=False
                # check number of waypoints?
            elif read_waypoints:
                # waypoints are given as two floats.
                self.add_waypoint(i)
                waypoint_counter+=1
            else:
                raise ValueError('Received unexpected line in mission file!')

    def addBehavior(self,i):
        behaviorName=i.split()[1]
        self.currentBehaviorName=behaviorName.lower()
        if behaviorName.lower() in list(ImplementedBehaviors.keys()):
            if self.verbose:print(behaviorName)
            b=ImplementedBehaviors[behaviorName]()
            self.behaviors.append(b)
        elif self.verbose:
            print("Ignoring %s, as it is not implemented."%(behaviorName))

    def add_waypoint(self,i):
        # this is a non-slocum specific method. It allows for waypoints to be 
        # put in mission files in the format used in the ma files. This is only
        # of use if a seaglider mission is simulated.
        if not self.currentBehaviorName in list(ImplementedBehaviors.keys()) or\
                self.currentBehaviorName!='goto_list':
            raise ValueError('Trying to read a waypoint datum, but I am not processing a goto_l behavior.')
        lon,lat=[float(k) for k in i.split()]
        behavior=self.behaviors[-1]
        behavior.waypoints.append((lon,lat))

    def addb_arg(self,i):
        if self.currentBehaviorName in list(ImplementedBehaviors.keys()):
            # only do something here if the behavior is implemented.
            dummy,param,value=i.split()
            # remove the units
            param=re.sub("\(.*\)","",param)
            try:
                valueNum=int(value)
            except ValueError:
                valueNum=float(value)
            b=self.behaviors[-1]
            b.__dict__[param]=valueNum
            if param=='args_from_file' and valueNum!=-1:
                fn=b.behaviorName.lower()
                if len(fn)>6:
                    fn=fn[:6]
                fn+=str(valueNum)+".ma"
                if b.behaviorName.lower()=='goto_list':
                    MA=MafileParserWpt(fn,b,self.mafileDirectory)
                    MA.parse()
                    MA.parseWpts()
                else:
                    MA=MafileParser(fn,b,self.mafileDirectory)
                    MA.parse()
    def set_sensor(self,i):
        words=i.split()
        parameter_name=words[1]
        value=words[2]
        # remove unit from parameter_name
        parameter_name=parameter_name.split("(")[0]
        value=float(value)
        self.sensor_settings.append((parameter_name,value))
        
if __name__=='__main__':
    MP=MissionParser('rapid.mi')
    MP.parse()
    
