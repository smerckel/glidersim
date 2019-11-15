import datetime
import json
from urllib import request
import os

import numpy as np
import netCDF4
from scipy.interpolate import interp1d, RegularGridInterpolator

import dbdreader
import latlonUTM
import timeconversion
import fast_gsw

class GliderData(object):
    ''' Class to compute environmental data based on glider data.

    Bathymetry data are from a netcdf file.
    '''
    
    BATHYMETRY_FILENAME = '/home/lucas/working/git/LMC/data/bathymetry.nc'
    GLIDERS_DIRECTORY = '/home/lucas/samba/gliders'
    AGE = 12 # Hours, use CTD data younger than this.
    
    def __init__(self, glider_name, gliders_directory=None):
        self.u_fun = None
        self.v_fun = None
        self.bathymetry_fun = None
        self.eos_fun = None
        self.glider_name = glider_name
        self.gliders_directory = gliders_directory or GliderData.GLIDERS_DIRECTORY
        
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

    def read_gliderdata(self, lat, lon):
        path = os.path.join(self.gliders_directory, self.glider_name, 'from-glider', '%s*.[st]bd'%(self.glider_name))
        dbd = dbdreader.MultiDBD(pattern=path)
        if self.glider_name == 'sim':
            print("Warning: assuming simulator. I am making up CTD data!")
            t, P = dbd.get("m_depth")
            P/=10
            C = np.ones_like(P)*4
            T = np.ones_like(P)*15
        else:
            tmp = dbd.get_sync("sci_water_cond", "sci_water_temp sci_water_pressure".split())
            t, C, T, P = tmp.compress(np.logical_and(tmp[1]>0, tmp[0][-1]-tmp[0]>self.AGE*3600), axis=1)
        rho = fast_gsw.rho(C*10, T, P*10, lon, lat)
        SA = fast_gsw.SA(C*10, T, P*10, lon, lat)
        # compute the age of each measurement, and the resulting weight.
        dt = t.max() - t
        weights = np.exp(-dt/(self.AGE*3600))
        # make binned averages
        max_depth = P.max()*10
        dz = 1
        zi = np.arange(dz/2, max_depth+dz/2, dz)
        bins = np.arange(0, max_depth+dz, dz)
        bins[0]=-10
        idx = np.digitize(P*10, bins)-1
        rho_avg = np.zeros_like(zi, float)
        SA_avg = np.zeros_like(zi, float)
        T_avg = np.zeros_like(zi, float)
        weights_sum = np.zeros_like(zi, float)
        for _idx, _w, _rho, _SA, _T in zip(idx, weights, rho, SA, T):
            try:
                rho_avg[_idx] += _rho*_w
                SA_avg[_idx] += _SA*_w
                T_avg[_idx] += _T*_w
                weights_sum[_idx] += _w
            except IndexError:
                continue
        rho_avg = rho_avg/weights_sum
        SA_avg = SA_avg/weights_sum
        T_avg = T_avg/weights_sum
        self.rho_fun = interp1d(zi, rho_avg, bounds_error = False, fill_value=(rho_avg[0], rho_avg[-1]))
        self.SA_fun = interp1d(zi, SA_avg, bounds_error = False, fill_value=(SA_avg[0], SA_avg[-1]))
        self.T_fun = interp1d(zi, T_avg, bounds_error = False, fill_value=(T_avg[0], T_avg[-1]))
            
    def initialise_velocity_data(self, t, lat, lon):
        self.u_fun = lambda x: 0
        self.v_fun = lambda x: 0
            
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
        if self.bathymetry_fun is None:
            self.initialise_velocity_data(t, lat, lon)
            self.read_bathymetry()
            self.read_gliderdata(lat, lon)

        u = float(self.u_fun(t))
        v = float(self.v_fun(t))
        w = 0
        water_depth = float(self.bathymetry_fun((lat, lon)))
        eta = 0
        # z is given as negative, but fitted against depth...
        S = float(self.SA_fun(-z))
        T = float(self.T_fun(-z))
        rho = float(self.rho_fun(-z))
        return u, v, w, water_depth, eta, S, T, rho


####################

class DriftModel(GliderData):
    ''' Class to compute environmental data based on the drift-now model.

    These data are queried like:

    curl "https://bn.hzg.de/cgi/input_drift.py?Time=2019_06_11_09_05&lat=54.99142&lon=5.01406&process_flag=1&Id=611625&Hours_nr=12&windfactors=0&Layer=-99" -o ./test.txt

    Bathymetry data are from a netcdf file.
    '''
    
    DATE_FORMAT_STR = "%d.%m.%Y %H:%M"
    INTERPOLATION_METHOD = 'quadratic'
    #INTERPOLATION_METHOD = 'linear'
    
    def __init__(self, glider_name, download_time=12):
        super().__init__(glider_name)
        self.download_time = download_time
        
    def download_drift_data(self, t, lat, lon):
        dt = datetime.datetime.utcfromtimestamp(t)
        tstr = "{:4d}_{:02d}_{:02d}_{:02d}_{:02d}".format(dt.year,
                                                          dt.month,
                                                          dt.day,
                                                          dt.hour,
                                                          dt.minute)
        s = "https://bn.hzg.de/cgi/input_drift.py?Time={}&lat={:3f}&lon={:3f}&process_flag=1&Id=611625&Hours_nr={:d}&windfactors=0&Layer=-99"
        url_address = s.format(tstr, lat, lon, self.download_time)
        u = request.urlopen(url_address)
        data = u.read()
        return self.parse_data(data)

        
    def parse_data(self, data):
        ''' Parse JSON data structure as returned by the drift-now api.

        Sets self.u_fun, and self.v_fun, interpolating functions for u and v, respectively.
        '''
        json_data = json.loads(data.decode('ascii'))
        x = []
        y = []
        t = []
        zone = None
        for _lon, _lat, tstr in json_data['Forward_output']:
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
        u_fun = interp1d(ti, np.gradient(fun_x(ti))/dt)
        v_fun = interp1d(ti, np.gradient(fun_y(ti))/dt)
        return u_fun, v_fun

    def initialise_velocity_data(self, t, lat, lon):
        ''' dowload drift data for this region and time '''
        self.u_fun, self.v_fun = self.download_drift_data(t, lat, lon)
