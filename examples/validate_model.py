import numpy as np
from matplotlib import pyplot as plt
from matplotlib.dates import epoch2num, DateFormatter
import dbdreader
from HZGnetCDF import ncHereon
import latlon

if 0:
    dbd_pattern = "../data/comet/from-glider/come*034.dbd"
    ncfilename = "comet-nsb3-spiral.nc"
else:
    dbd_pattern = "../data/comet/from-glider/comet-2019-222-02-15[456].dbd"
    ncfilename = "comet-nsb3-nsb3.nc"

mavg = lambda x,y : np.convolve(x, np.ones(y)/y, 'same')

dbd = dbdreader.MultiDBD(pattern=dbd_pattern, complement_files=True, cacheDir='../data/cac')
dd = dict(m_depth=dbd.get("m_depth"),
          m_pitch=dbd.get("m_pitch"),
          m_heading=dbd.get("m_heading"),
          c_heading=dbd.get("c_heading"),
          m_ballast_pumped=dbd.get("m_ballast_pumped"),
          m_x_lmc = dbd.get("m_x_lmc"),
          m_y_lmc = dbd.get("m_y_lmc"),
          m_fin = dbd.get("m_fin"),
          m_lat = dbd.get("m_lat"),
          m_lon = dbd.get("m_lon"),
          m_speed = dbd.get("m_speed"),
          m_water_vx = dbd.get("m_water_vx"),
          m_water_vy = dbd.get("m_water_vy"),
          m_depth_rate = dbd.get("m_depth_rate"),
          m_roll = dbd.get("m_roll"),
          m_battpos = dbd.get("m_battpos")
          )


with ncHereon(ncfilename, mode='r') as nc:
    ts, ds = nc.get("m_depth")
    ts, pitchs = nc.get("m_pitch")
    ts, headings = nc.get("m_heading")
    ts, cheadings = nc.get("c_heading")
    ts, buoyancys = nc.get("m_ballast_pumped")
    ts, fins = nc.get("m_fin")
    ts, xs = nc.get("m_lmc_x")
    ts, ys = nc.get("m_lmc_y")
    ts, xxs = nc.get("x_lmc_x")
    ts, xys = nc.get("x_lmc_y")
    ts, us = nc.get("x_u")
    ts, vs = nc.get("x_v")
    ts, lats = nc.get("m_lat")
    ts, lons = nc.get("m_lon")
    ts, speeds = nc.get("m_speed")
    ts, depthrates = nc.get("x_upward_glider_velocity"); depthrates *=-1
    ts, battposs = nc.get("m_battpos")
    lons = latlon.convertToDecimal(lons)
    lats = latlon.convertToDecimal(lats)
    v = nc.dataset.variables.keys()
    
f, ax = plt.subplots(4,2, sharex=True, figsize=(12, 6))

ax[0,0].plot(epoch2num(ts), ds, label='simulation')
ax[0,0].plot(epoch2num(dd['m_depth'][0]), dd['m_depth'][1], label='glider')

ax[1,0].plot(epoch2num(ts), pitchs, label='simulation')
ax[1,0].plot(epoch2num(dd['m_pitch'][0]), dd['m_pitch'][1], label='glider')

ax[0,1].plot(epoch2num(ts), headings, label='simulation')
ax[0,1].plot(epoch2num(dd['m_heading'][0]), dd['m_heading'][1], label='glider')
ax[0,1].plot(epoch2num(ts), cheadings, label='simulation')
ax[0,1].plot(epoch2num(dd['c_heading'][0]), dd['c_heading'][1], label='glider')

ax[1,1].plot(epoch2num(ts), buoyancys, label='simulation')
ax[1,1].plot(epoch2num(dd['m_ballast_pumped'][0]), dd['m_ballast_pumped'][1], label='glider')

ax[2,0].plot(epoch2num(ts), fins, label='simulation')
ax[2,0].plot(epoch2num(dd['m_fin'][0]), dd['m_fin'][1], label='glider')

ax[2,1].plot(epoch2num(ts), speeds, label='simulation')
ax[2,1].plot(epoch2num(dd['m_speed'][0]), mavg(dd['m_speed'][1], 15), label='glider')

ax[3,0].plot(epoch2num(ts), depthrates, label='simulation')
ax[3,0].plot(epoch2num(dd['m_depth_rate'][0]), mavg(dd['m_depth_rate'][1], 15), label='glider')

ax[3,1].plot(epoch2num(ts), battposs, label='simulation')
ax[3,1].plot(epoch2num(dd['m_battpos'][0]), mavg(dd['m_battpos'][1], 15), label='glider')

fmt = DateFormatter("%H:%M\n%d/%m")
ax[1,1].xaxis.set_major_formatter(fmt)
ax[1,0].xaxis.set_major_formatter(fmt)
ax[0,0].set_ylabel('Depth (m)')
ax[1,0].set_ylabel('Pitch (rad)')
ax[0,1].set_ylabel('Heading (rad)')
ax[1,1].set_ylabel('Buoyancy drive (cc)')
ax[2,0].set_ylabel('Fin position (rad)')
ax[2,1].set_ylabel('Speed (m/s)')
ax[3,0].set_ylabel('Depth rate (m/s)')
ax[3,1].set_ylabel('Batt. pos. (inch)')


f1, bx = plt.subplots(1,2, squeeze=False, figsize=(12,6))
x0 = dd["m_x_lmc"][1][0]
y0 = dd["m_y_lmc"][1][0]

bx[0,0].plot(xs, ys, marker='.', label='simulation (deadreckoned)')
bx[0,0].plot(dd["m_x_lmc"][1]-x0,dd["m_y_lmc"][1]-y0, marker='.', label='glider')
bx[0,0].plot(xxs, xys, marker='.', label='simulation')
bx[0,0].set_xlabel('x (m)')
bx[0,0].set_ylabel('y (m)')

bx[0,1].plot(lons, lats, marker='.', label='simulation (deadreckoned)')
bx[0,1].plot(dd["m_lon"][1],dd["m_lat"][1], marker='.', label='glider')
bx[0,0].set_aspect(1)
bx[0,1].set_xlabel('lon (deg)')
bx[0,1].set_ylabel('lat (deg)')

#plt.show()
