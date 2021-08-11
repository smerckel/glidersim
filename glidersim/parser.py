import re
import os

from . import behaviors

ImplementedBehaviors={'abend':behaviors.Abend,
                      'yo':behaviors.Yo,
                      'sgyo':behaviors.SGYo,
                      'dive_to':behaviors.Dive_to,
                      'climb_to':behaviors.Climb_to,
                      'goto_list':behaviors.Goto_list,
                      'surface':behaviors.Surface,
                      'sample': behaviors.Sample,
                      'sensors_in':behaviors.Sensors_in,
                      'prepare_to_dive':behaviors.Prepare_to_dive,
                      'set_heading':behaviors.Set_heading}

           

class MafileParser(object):
    def __init__(self,filename=None,behavior=None,mafileDirectory='mafiles'):
        self.filename=filename
        self.behavior=behavior
        self.mafileDirectory=mafileDirectory
        
    def parse(self):
        with open(os.sep.join([self.mafileDirectory,self.filename])) as fp:
            lines=fp.readlines()
        self.lines = self.__parse(lines)

    def parses(self, s):
        lines=s.split("\n")
        self.lines = self.__parse(lines)
        
    def __parse(self, lines):
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
        return lines

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
        b.b_arg_parameters.append(param)
        
class MafileParserWpt(MafileParser):
    def __init__(self,filename=None ,behavior=None, mafileDirectory='mafiles'):
        MafileParser.__init__(self,filename,behavior,mafileDirectory)

    def parses(self,s):
        super().parses(s)
        self.parseWpts()
        
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
        i=0
        while True:
            if not len(lines):
                break
            line=lines.pop(0)
            if line=='<end:waypoints>':
                break
            lon,lat=line.split()
            lon=float(lon)
            lat=float(lat)
            i+=1
            self.behavior.waypoints.append((lon,lat))
        if i != self.behavior.num_waypoints: 
            raise ValueError('Probably a malformed ma file. Number of waypoints incorrect')

class MissionParser(object):
    def __init__(self, verbose=True):
        self.behaviors=[]
        self.currentBehaviorName=None
        self.sensor_settings=[]
        self.verbose=verbose
        self.mafiles=[]
        verbose=True
        behaviors.VERBOSE = verbose
        
    def parse(self, mission, mafile_directory, raise_error_on_missing_mafiles=True):
        with open(mission, 'r') as fp:
            lines = fp.readlines()
        self.lines = self.__parse(lines, mafile_directory, raise_error_on_missing_mafiles)
        return self.mafiles
        
    def __parse(self, lines, mafile_directory, raise_error_on_missing_mafiles):
        # remove any leading spaces:
        lines=[i.strip() for i in lines]
        # remove any comments:
        lines=[re.sub("#.*$","",i) for i in lines]
        # remove blanks:
        lines=[i for i in lines if i]
        for i in lines:
            if i.startswith("behavior:"):
                self.addBehavior(i)
            elif i.startswith("b_arg:"):
                self.addb_arg(i, mafile_directory, raise_error_on_missing_mafiles)
            elif i.startswith("sensor:"):
                self.set_sensor(i)
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

    def addb_arg(self,i, mafile_directory, raise_error_on_missing_mafiles):
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
            b.b_arg_parameters.append(param)
            if param=='args_from_file' and valueNum!=-1:
                fn=b.behaviorName.lower()
                if len(fn)>6:
                    fn=fn[:6]
                fn+=str(valueNum)+".ma"
                self.mafiles.append(fn)
                try:
                    if b.behaviorName.lower()=='goto_list':
                        MA=MafileParserWpt(fn,b,mafile_directory)
                        MA.parse()
                        MA.parseWpts()
                    else:
                        MA=MafileParser(fn,b,mafile_directory)
                        MA.parse()
                except FileNotFoundError as e:
                    if raise_error_on_missing_mafiles:
                        raise e
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
    
