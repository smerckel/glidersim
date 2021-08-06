import sys; sys.path.insert(0, "..")
import unittest

import numpy as np

import glidersim.environments as env

env.GliderData.NC_ELEVATION_NAME='bathymetry'
env.GliderData.NC_LAT_NAME='latc'
env.GliderData.NC_LON_NAME='lonc'

class Environments_driftmodel_test(unittest.TestCase):
    def __init__(self, *p):
        super().__init__(*p)
        self.dm = env.DriftModel('comet', download_time=12, gliders_directory='../data', bathymetry_filename='../data/bathymetry.nc')

    def test_create_interpolating_velocity_functions(self):
        u_fun, v_fun = self.dm.download_drift_data(1565364000, 54, 7)
        assert np.abs(u_fun(1565364000)-0.49077213)<1e-4
        
    def test_get_data(self):
        u, v, w, water_depth, eta, S, T, rho = self.dm.get_data(1565364000, 54, 7, -5)
        assert np.abs(u-0.49077213)<1e-4 and np.abs(rho-1024.3827138)<1e-3

#e = Environments_driftmodel_test()

# suppress any info messages:
env.logger.setLevel(env.logging.ERROR)

unittest.main()        
