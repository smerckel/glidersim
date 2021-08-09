import numpy as np
from matplotlib import pyplot as plt
from matplotlib.dates import epoch2num, DateFormatter
import dbdreader
from HZGnetCDF import ncHereon

dbd_pattern = "../data/comet/from-glider/come*034.dbd"
ncfilename = "comet-nsb3-spiral.nc"

dbd_pattern = "../data/comet/from-glider/comet-2019-222-02-154.dbd"
ncfilename = "comet-nsb3-nsb3.nc"



dbd = dbdreader.MultiDBD(pattern=dbd_pattern, complement_files=True, cacheDir='../data/cac')
dd = dict(m_depth=dbd.get("m_depth"),
          m_pitch=dbd.get("m_pitch"),
          m_heading=dbd.get("m_heading"),
          m_ballast_pumped=dbd.get("m_ballast_pumped"),
          m_x_lmc = dbd.get("m_x_lmc"),
          m_y_lmc = dbd.get("m_y_lmc"),
          )


with ncHereon(ncfilename, mode='r') as nc:
    ts, ds = nc.get("m_depth")
    ts, pitchs = nc.get("m_pitch")
    ts, headings = nc.get("m_heading")
    ts, buoyancys = nc.get("m_ballast_pumped")
    ts, xs = nc.get("m_lmc_x")
    ts, ys = nc.get("m_lmc_y")
    ts, xxs = nc.get("x_lmc_x")
    ts, xys = nc.get("x_lmc_y")
    ts, us = nc.get("x_u")
    ts, vs = nc.get("x_v")
    ts, lats = nc.get("m_lat")
    ts, lons = nc.get("m_lon")
    v = nc.dataset.variables.keys()
    
f, ax = plt.subplots(2,2, sharex=True)

ax[0,0].plot(epoch2num(ts), ds, label='simulation')
ax[0,0].plot(epoch2num(dd['m_depth'][0]), dd['m_depth'][1], label='glider')

ax[1,0].plot(epoch2num(ts), pitchs, label='simulation')
ax[1,0].plot(epoch2num(dd['m_pitch'][0]), dd['m_pitch'][1], label='glider')

ax[0,1].plot(epoch2num(ts), headings, label='simulation')
ax[0,1].plot(epoch2num(dd['m_heading'][0]), dd['m_heading'][1], label='glider')

ax[1,1].plot(epoch2num(ts), buoyancys, label='simulation')
ax[1,1].plot(epoch2num(dd['m_ballast_pumped'][0]), dd['m_ballast_pumped'][1], label='glider')

fmt = DateFormatter("%H:%M\n%d\%m")
ax[1,1].xaxis.set_major_formatter(fmt)
ax[1,0].xaxis.set_major_formatter(fmt)
ax[0,0].set_ylabel('Depth (m)')
ax[1,0].set_ylabel('Pitch (rad)')
ax[0,1].set_ylabel('Heading (rad)')
ax[1,1].set_ylabel('Buoyancy drive (cc)')


f1, bx = plt.subplots(1,1)
x0 = dd["m_x_lmc"][1][0]
y0 = dd["m_y_lmc"][1][0]

bx.plot(dd["m_x_lmc"][1]-x0,dd["m_y_lmc"][1]-y0, marker='.', label='glider')
bx.plot(xs, ys, marker='.', label='simulation (deadreckoned)')
bx.plot(xxs, xys, marker='.', label='simulation')
bx.set_xlabel('x (m)')
bx.set_ylabel('y (m)')

plt.show()
