import os
import re
import datetime

class Config(object):
    def __init__(self,
                 missionName,
                 datestr=None,
                 timestr=None,
                 lat_ini=None,
                 lon_ini=None,
                 dt = 1,
                 rho0 = 1025,
                 **kw):
        self.description=""
        self.missionName=missionName
        self.datestr=datestr
        self.timestr=timestr
        self.lat_ini=lat_ini
        self.lon_ini=lon_ini
        self.dt = dt
        self.rho0 = rho0
        self.storePeriod=10
        self.mission_directory='experiment'
        self.mission_start='initial'
        self.output=None
        self.sensor_settings={}
        self.special_settings={}
        self.longtermParameters=[]
        for k,v in kw.items():
            self.__dict__[k]=v

    def __modifyOutput(self):
        basename=self.output.replace(".pck","")
        x=re.search("\([0-9]*?\)$",basename)
        if x:
            xx=x.group()
            s=xx.replace("(","").replace(")","")
            r="%d"%(int(s)+1)
            basename=re.sub("\(%s\)"%(s),"(%s)"%(r),basename)
        else:
            basename+="(1)"
        self.output=basename+".pck"
    
    def set_start_date(self):
        x=datetime.datetime.strptime(self.datestr+self.timestr,"%Y%m%d%H:%M")
        self.start_date=x.strftime("%d %b %Y %H:%M")

    def set_sensors(self,GM):
        for sensorname,sensorvalue in self.sensor_settings.items():
            GM.sensor(sensorname,sensorvalue)

    def set_special_settings(self,GM):
        for k,v in self.special_settings.items():
            print("setting:", k,v)
            GM.__dict__[k]=v

    def checkOutputFilename(self):
        while True:
            if os.path.exists(self.output):
                self.__modifyOutput()
            else:
                break
        print("Saving into %s"%(self.output))
        input("Press key to continue")

