import math
from latlonUTM import UTM2latlon
from latlon import convertToNmea, convertToDecimal
from . import getm
import glob
import numpy as np
from scipy.interpolate import interp2d, interp1d
from .timeconversion import strptimeToEpoch

import random

class TimeseriesEnvironment(object):
    BATHYMETRY=None
    NCBATHYMETRY='/home/lucas/getm_data/getm3d/bathymetry.nc'
    DEFAULT_DEPTH=40

    def __init__(self):
        self.bathymetry=getm.Bathymetry(self.NCBATHYMETRY)
        self.__warning_counter=0
    def set_data(self,t,u,v):
        self.t=t
        self.u=interp1d(t,u)
        self.v=interp1d(t,v)

    def get_current(self,t,lat,lon,z, convert_to_decimal=True):
        ''' returns netcdf data for u, S T eta and depth for given
            lat/lon and interpolated to glider time.
        '''
        if convert_to_decimal:
            dec_lat=convertToDecimal(lat)
            dec_lon=convertToDecimal(lon)
        else:
            dec_lat=lat
            dec_lon=lon
        try:
            d=self.bathymetry.get_water_depth(dec_lat,dec_lon)
        except:
            if self.__warning_counter==0:
                print("Failed to read water depth from NC file. Use default value.")
                self.__warning_counter+=1
            d=TimeseriesEnvironment.DEFAULT_DEPTH
        u=self.u(t)
        v=self.v(t)
        w=0
        dp=d
        eta=0
        S=self.Sref
        T=self.Tref
        return u,v,w,dp,eta,S,T


class OneDimEnvironment(object):
    DEFAULT_DEPTH=1000

    def set_data(self,z,rho_in_situ):
        self.profile_data=dict(z=z,
                               rho_in_situ=rho_in_situ)

    def get_current(self,t,lat,lon,z, convert_to_decimal=True):
        ''' returns netcdf data for u, S T eta and depth for given
            lat/lon and interpolated to glider time.
        '''
        d=OneDimEnvironment.DEFAULT_DEPTH
        u=0
        v=0
        w=0
        dp=d
        eta=0
        S=np.nan
        T=np.interp(z,self.profile_data['z'],self.profile_data['rho_in_situ'])
        return u,v,w,dp,eta,S,T

