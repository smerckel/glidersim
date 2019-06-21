import datetime
import json
import urllib

import numpy as np
import netCDF4
from scipy.interpolate import interp1d, RegularGridInterpolator

import latlonUTM
import timeconversion

class DriftModel(object):
    ''' Class to compute environmental data based on the drift-now model.

    These data are queried like:

    curl "https://bn.hzg.de/cgi/input_drift.py?Time=2019_06_11_09_05&lat=54.99142&lon=5.01406&process_flag=1&Id=611625&Hours_nr=12&windfactors=0&Layer=-99" -o ./test.txt

    Bathymetry data are from a netcdf file.
    '''
    
    DATE_FORMAT_STR = "%d.%m.%Y %H:%M"
    INTERPOLATION_METHOD = 'quadratic'
    BATHYMETRY_FILENAME = '/home/lucas/working/git/LMC/data/bathymetry.nc'
    
    def __init__(self):
        self.u_fun = None
        self.v_fun = None
        self.bathymetry_fun = None
        
    def download_drift_data(self, t, lat, lon):
        dt = datetime.datetime.utcfromtimestamp(t)
        tstr = "{:4d}_{:02d}_{:02d}_{:02d}_{:02d}".format(dt.year,
                                                          dt.month,
                                                          dt.day,
                                                          dt.hour,
                                                          dt.minute)
        s = "https://bn.hzg.de/cgi/input_drift.py?Time={}&lat={:3f}&lon={:3f}&process_flag=1&Id=611625&Hours_nr={:d}&windfactors=0&Layer=-99"
        url_address = s.format(tstr, lat, lon, 12)
        u = urllib.request.urlopen(url_address)
        data = u.read()
        self.parse_data(data)

        
    def parse_data(self, data):
        ''' Parse JSON data structure as returned by the drift-now api.

        Sets self.u_fun, and self.v_fun, interpolating functions for u and v, respectively.
        '''
        json_data = json.loads(data.decode('ascii'))
        x = []
        y = []
        t = []
        zone = None
        for _lon, _lat, tstr in json_data['Forword_output']:
            _t = timeconversion.strptimeToEpoch(tstr, self.DATE_FORMAT_STR)
            t.append(_t)
            (_x, _y), _zone, _ = latlonUTM.latlon2UTM(_lat, _lon)
            if zone is None:
                zone = _zone
            offset = latlonUTM.zonalOffset(_lat, _lon, zone)
            x.append(_x + offset)
            y.append(_y)
            

        fun_x = interp1d(t, x, kind=self.INTERPOLATION_METHOD)
        fun_y = interp1d(t, y, kind=self.INTERPOLATION_METHOD)
        dt = 60
        ti = np.arange(t[0], t[-1], dt)
        self.u_fun = interp1d(ti, np.gradient(fun_x(ti))/dt)
        self.v_fun = interp1d(ti, np.gradient(fun_y(ti))/dt)
        
    def read_bathymetry(self):
        ''' Read bathymetry from a netcdf file

        Sets self.bathymetry_fun
        '''
        dataset = netCDF4.Dataset(self.BATHYMETRY_FILENAME, 'r', keepweakref=True)
        bathymetry = dataset.variables['bathymetry'][...].copy()
        lat = dataset.variables['latc'][...].copy()
        lon = dataset.variables['lonc'][...].copy()
        dataset.close()
        self.bathymetry_fun = RegularGridInterpolator((lat, lon), bathymetry)

    def get_data(self, t, lat, lon, z):
        ''' Standard interface, getting environmental parameters:

        Parameters
        ----------
        
        t : float
            time
        lat : float
            decimal latitude
        lon : float
            decimal longitude
        z : float 
            vertical coordinate (z<=0)
        '''
        if self.u_fun is None:
            self.download_drift_data(t, lat, lon)
            self.read_bathymetry()
        u = self.u_fun(t)
        v = self.v_fun(t)
        w = 0
        water_depth = self.bathymetry_fun((lat, lon))
        eta = 0
        S = 35
        T = 10
        rho = 1025
        return u, v, w, water_depth, eta, S, T, rho
