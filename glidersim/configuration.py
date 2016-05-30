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
                 **kw):
        self.description=""
        self.missionName=missionName
        self.datestr=datestr
        self.timestr=timestr
        self.lat_ini=lat_ini
        self.lon_ini=lon_ini
        self.storePeriod=10
        self.directory='/home/lucas/getm_data/kofserver2'
        self.basename='getm3d_'
        self.suffix='.nc'
        self.mafiles='mafiles'
        self.missions='missions'
        self.output=None
        self.sensor_settings={}
        self.special_settings={}
        self.longtermParameters=[]
        for k,v in kw.items():
            self.__dict__[k]=v
        #self.set_start_date()

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
        for sensorname,sensorvalue in self.sensor_settings:
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

class ConfigurationDictionary(dict):
    ''' subclassed dictionary that checks whether self.output is set, and
        if not, it will set it to key.pck '''
    def __init__(self,*args,**kws):
        dict.__init__(self,*args,**kws)

    def __getitem__(self,key):
        value=dict.__getitem__(self,key)
        if value.output==None:
            value.output="%s.pck"%(key)
        return value


if 0:
    configurations=ConfigurationDictionary()

    configurations['gb_drift_0']=Config('gb-drift.mi',
                                        description="drifting glider NW helgoland",
                                        datestr='20100519',
                                        timestr='00:30',
                                        lat_ini=5413.000,
                                        lon_ini=740.500,
                                        output='gb_drift.pck',
                                        sensor_settings=[('u_use_current_correction',0)],
                                        special_settings=['glider.gps.acquiretime=310000.'])


    configurations['gb_drift_1']=Config('gb-drift.mi',
                                        description="drifting glider NW helgoland from second waypoint",
                                        datestr='20100519',
                                        timestr='00:30',
                                        lat_ini=5429.000,
                                        lon_ini=715.750,
                                        output='gb_drift_1.pck',
                                        sensor_settings=[('u_use_current_correction',0)],
                                        special_settings=['glider.gps.acquiretime=310000.'])

    configurations['gb_drift_2']=Config('gb-drift.mi',
                                        description="drifting glider NW helgoland in quiet area",
                                        datestr='20100519',
                                        timestr='00:30',
                                        lat_ini=5412.000,
                                        lon_ini=730.000,
                                        output='gb_drift_2.pck',
                                        sensor_settings=[('u_use_current_correction',0)],
                                        special_settings=['glider.gps.acquiretime=310000.'])



    configurations['gb_east_transect']=Config('gb-east-transect-21.mi',
                                              description="drifting glider NW helgoland in quiet area",
                                              datestr='20100501',
                                              timestr='00:30',
                                              lat_ini=5414.700,
                                              lon_ini=747.400,
                                              output='gb_east_transect_0.pck',
                                              sensor_settings=[('u_use_current_correction',0)])


    configurations['sylt_1']=Config('sylt.mi',
                                        description="deployment near sylt",
                                        datestr='20100507',
                                        timestr='12:00',
                                        lat_ini=5503.120,
                                        lon_ini=825.860,
                                        output='sylt_1.pck',
                                        sensor_settings=[('u_use_current_correction',0)])

    configurations['sylt_2']=Config('sylt.mi',
                                        description="deployment near sylt",
                                        datestr='20100507',
                                        timestr='16:00',
                                        lat_ini=5503.120,
                                        lon_ini=825.860,
                                        output='sylt_2.pck',
                                        sensor_settings=[('u_use_current_correction',0)])
    configurations['sylt_3']=Config('sylt.mi',
                                        description="deployment near sylt",
                                        datestr='20100507',
                                        timestr='18:00',
                                        lat_ini=5503.120,
                                        lon_ini=825.860,
                                        output='sylt_3.pck',
                                        sensor_settings=[('u_use_current_correction',0)])

    configurations['sylt_4']=Config('sylt.mi',
                                        description="deployment near sylt",
                                        datestr='20100507',
                                        timestr='20:00',
                                        lat_ini=5503.120,
                                        lon_ini=825.860,
                                        output='sylt_4.pck',
                                        sensor_settings=[('u_use_current_correction',0)])

    configurations['sylt_5']=Config('sylt_1.mi',
                                        description="deployment near sylt",
                                        datestr='20100507',
                                        timestr='18:00',
                                        lat_ini=5503.120,
                                        lon_ini=825.860,
                                        output='sylt_5.pck',
                                        sensor_settings=[('u_use_current_correction',0)])

    configurations['sylt_6']=Config('sylt_4.mi',
                                        description="deployment near sylt",
                                        datestr='20100507',
                                        timestr='18:00',
                                        lat_ini=5503.120,
                                        lon_ini=825.860,
                                        output='sylt_6.pck',
                                        sensor_settings=[('u_use_current_correction',0)])

    configurations['sylt_7']=Config('sylt.mi',
                                        description="deployment near sylt",
                                        datestr='20100507',
                                        timestr='18:00',
                                        lat_ini=5503.120,
                                        lon_ini=825.860,
                                        output='sylt_7.pck',
                                        sensor_settings=[('u_use_current_correction',1)])
    configurations['sylt_8']=Config('sylt_2.mi',
                                        description="deployment near sylt",
                                        datestr='20100507',
                                        timestr='18:00',
                                        lat_ini=5503.120,
                                        lon_ini=825.860,
                                        output='sylt_8.pck',
                                        sensor_settings=[('u_use_current_correction',0)])

    configurations['sylt_9']=Config('sylt_3.mi',
                                        description="deployment near sylt",
                                        datestr='20100507',
                                        timestr='18:00',
                                        lat_ini=5503.120,
                                        lon_ini=825.860,
                                        output='sylt_9.pck',
                                        sensor_settings=[('u_use_current_correction',0)])
    configurations['line_1']=Config('line.mi',
                                        description="endurance line NSboje and deutsche bucht",
                                        datestr='20100501',
                                        timestr='12:00',
                                        lat_ini=5410.000,
                                        lon_ini=727.000,
                                        output='line_1.pck',
                                        sensor_settings=[('u_use_current_correction',0)])

    configurations['line_2']=Config('line.mi',
                                        description="endurance line NSboje and deutsche bucht",
                                        datestr='20100501',
                                        timestr='12:00',
                                        lat_ini=5410.000,
                                        lon_ini=727.000,
                                        output='line_2.pck',
                                        sensor_settings=[('u_use_current_correction',1)])


    configurations['line_3']=Config('line_3.mi',
                                        description=
    """endurance line NSboje and deutsche bucht
       24 yo's instead of 8 (2 hours instead of 0.5)
    """,
                                        datestr='20100501',
                                        timestr='12:00',
                                        lat_ini=5410.000,
                                        lon_ini=727.000,
                                        output='line_3.pck',
                                        sensor_settings=[('u_use_current_correction',0)])

    configurations['line_4']=Config('line_3.mi',
                                        description=
    """endurance line NSboje and deutsche bucht
       24 yo's instead of 8 (2 hours instead of 0.5)
    """,
                                        datestr='20100501',
                                        timestr='12:00',
                                        lat_ini=5410.000,
                                        lon_ini=727.000,
                                        output='line_4.pck',
                                        sensor_settings=[('u_use_current_correction',1)])


    configurations['line_5']=Config('line5.mi',
                                        description="endurance line NSboje and deutsche bucht, as 1, but back and forth",
                                        datestr='20100501',
                                        timestr='12:00',
                                        lat_ini=5410.000,
                                        lon_ini=727.000,
                                        output='line_5.pck',
                                        sensor_settings=[('u_use_current_correction',0)])

    configurations['line_6']=Config('line5.mi',
                                        description="endurance line NSboje and deutsche bucht, as 1, but back and forth",
                                        datestr='20100501',
                                        timestr='12:00',
                                        lat_ini=5410.000,
                                        lon_ini=727.000,
                                        output='line_6.pck',
                                        sensor_settings=[('u_use_current_correction',1)])


