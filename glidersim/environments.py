import datetime
import json
from urllib import request
import os
import logging

import numpy as np
import netCDF4
from scipy.interpolate import interp1d, RegularGridInterpolator

import dbdreader
import latlonUTM
import timeconversion
import fast_gsw

logger = logging.getLogger(name="environments")
logger.setLevel(logging.INFO)

class GliderData(object):
    ''' Class to compute environmental data based on glider data.

    Bathymetry data are from a netcdf file.
    '''
    
    BATHYMETRY_FILENAME = '/home/lucas/working/git/LMC/data/bathymetry_CV.nc'
    GLIDERS_DIRECTORY = '/home/lucas/samba/gliders'
    AGE = 12 # Hours, use CTD data younger than this.
    NC_ELEVATION_NAME = 'elevation'
    NC_ELEVATION_FACTOR = -1
    NC_LAT_NAME = 'lat'
    NC_LON_NAME = 'lon'
    DBDREADER_CACHEDIR = None
    
    def __init__(self, glider_name, gliders_directory=None, bathymetry_filename=None):
        self.u_fun = None
        self.v_fun = None
        self.bathymetry_fun = None
        self.eos_fun = None
        self.glider_name = glider_name
        self.gliders_directory = gliders_directory or GliderData.GLIDERS_DIRECTORY
        self.bathymetry_filename = bathymetry_filename or GliderData.BATHYMETRY_FILENAME
        self._print_warnings = True

    def reset(self):
        '''
        Causes a reload of data
        '''
        self.bathymetry_fun = None
        
    def read_bathymetry(self):
        ''' Read bathymetry from a netcdf file

        Sets self.bathymetry_fun
        '''
        dataset = netCDF4.Dataset(self.bathymetry_filename, 'r', keepweakref=True)
        bathymetry = self.NC_ELEVATION_FACTOR * dataset.variables[self.NC_ELEVATION_NAME][...].copy()
        lat = dataset.variables[self.NC_LAT_NAME][...].copy()
        lon = dataset.variables[self.NC_LON_NAME][...].copy()
        dataset.close()
        self.bathymetry_fun = RegularGridInterpolator((lat, lon), bathymetry)

    def read_gliderdata(self, lat, lon):
        path = os.path.join(self.gliders_directory, self.glider_name, 'from-glider', '%s*.[st]bd'%(self.glider_name))
        dbd = dbdreader.MultiDBD(pattern=path, cacheDir=self.DBDREADER_CACHEDIR)
        if self.glider_name == 'sim':
            print("Warning: assuming simulator. I am making up CTD data!")
            t, P = dbd.get("m_depth")
            P/=10
            C = np.ones_like(P)*4
            T = np.ones_like(P)*15
            u = np.zeros(1, float)
            v = u.copy()
        else:
            tmp = dbd.get_sync(*"sci_water_cond sci_water_temp sci_water_pressure".split())
            t_last = tmp[0][-1]
            age = t_last - tmp[0]
            t, C, T, P = np.compress(np.logical_and(tmp[1]>0, age<self.AGE*3600), tmp, axis=1)
            try:
                _, u, v = dbd.get_sync("m_water_vx", "m_water_vy")
            except dbdreader.DbdError:
                try:
                    _, u, v = dbd.get_sync("m_final_water_vx", "m_final_water_vy")
                except dbdreader.DbdError:
                    u = np.array([0])
                    v = np.array([0])
            u, v = np.compress(np.logical_and(np.abs(u)<1.5, np.abs(v)<1.5), [u, v], axis=1)
        dbd.close()
        rho = fast_gsw.rho(C*10, T, P*10, lon, lat)
        SA = fast_gsw.SA(C*10, T, P*10, lon, lat)
        # compute the age of each measurement, and the resulting weight.
        dt = t.max() - t
        weights = np.exp(-dt/(self.AGE*3600))
        # make binned averages
        max_depth = P.max()*10
        dz = 5
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
        # if data are sparse, it can be that ther are gaps
        j = np.unique(idx)
        zj = zi[j]
        rho_avg = rho_avg[j]/weights_sum[j]
        SA_avg = SA_avg[j]/weights_sum[j]
        T_avg = T_avg[j]/weights_sum[j]
        self.rho_fun = interp1d(zj, rho_avg, bounds_error = False, fill_value=(rho_avg[0], rho_avg[-1]))
        self.SA_fun = interp1d(zj, SA_avg, bounds_error = False, fill_value=(SA_avg[0], SA_avg[-1]))
        self.T_fun = interp1d(zj, T_avg, bounds_error = False, fill_value=(T_avg[0], T_avg[-1]))

        if self.u_fun is None: # not intialised yet, use last water current estimate available.
            self.u_fun = lambda x : u[-1]
            self.v_fun = lambda x : v[-1]
        
    def initialise_velocity_data(self, t, lat, lon):
        #self.u_fun = lambda x: 0
        #self.v_fun = lambda x: 0
        pass
    
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
        try:
            u = float(self.u_fun(t))
            v = float(self.v_fun(t))
        except NameError:
            u=v=0
        w = 0
        try:
            water_depth = float(self.bathymetry_fun((lat, lon)))
        except ValueError:
            if self._print_warnings:
                print("Could not get water depth. Setting waterdepth to 200")
            self._print_warnings=False
            water_depth = 200
        if water_depth < 0:
            logger.error(f"Waterdepth found to be negative ({water_depth}). It could be that the bathymetry is\n\tgiven with the opposite sign as expected.\n\tTry to reverse sign of glidersim.environts.NC_ELEVATION_FACTOR")
        
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

    curl "https://hcdc.hzg.de/lcgi/DriftApp/GetTrajectories.py?Id=952&Time=2019_08_09_15_20&windfactors=0&Layer=-99&StartPoint=[[6.12368,55.18006],[6.776032,54.668498]]&process_flag=1&Hours_nr=24" -o ./test.txt

    Bathymetry data are from a netcdf file.
    '''
    
    DATE_FORMAT_STR = "%d.%m.%Y %H:%M"
    INTERPOLATION_METHOD = 'quadratic' # or 'linear'
    
    def __init__(self, glider_name, download_time=12, gliders_directory=None, bathymetry_filename=None):
        super().__init__(glider_name, gliders_directory, bathymetry_filename)
        self.download_time = download_time
        
    def download_drift_data(self, t, lat, lon):
        logger.info("Requesting current info from DrfitApp-server...")
        dt = datetime.datetime.utcfromtimestamp(t)
        tstr = "{:4d}_{:02d}_{:02d}_{:02d}_{:02d}".format(dt.year,
                                                          dt.month,
                                                          dt.day,
                                                          dt.hour,
                                                          dt.minute)
        s = "https://hcdc.hzg.de/lcgi/DriftApp/GetTrajectories.py?Id=952&Time={}&windfactors=0&Layer=-99&StartPoint=[{:3f},{:3f}]&process_flag=1&Hours_nr={:d}"

        #s = "https://bn.hereon.de/cgi/input_drift.py?Time={}&lat={:3f}&lon={:3f}&process_flag=1&Id=611625&Hours_nr={:d}&windfactors=0&Layer=-99"
        url_address = s.format(tstr, lon, lat, self.download_time)
        u = request.urlopen(url_address)
        data = u.read()
        logger.info("Request processed.")
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
        for _lon, _lat, *_, tstr in json_data['Forward_output']:
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
