import glidersim
import pylab as pl
import dbdreader 
from latlon import convertToDecimal as deg


data = glidersim.dataviz.Data({})
data.load('helgo-compare.pck')
dbds = dbdreader.MultiDBD(pattern = 'gd/*.dbd')

t = data.get('m_present_time')
d = data.get('m_depth')
wd = data.get('x_water_depth')
b = data.get('m_ballast_pumped')
bp = data.get('m_battpos')
cbp = data.get('c_battpos')

p = data.get('m_pitch')
xlat = deg(data.get('x_lat'))
xlon = deg(data.get('x_lon'))
lat = deg(data.get('m_lat'))
lon = deg(data.get('m_lon'))

dd = dbds.get('m_depth')
pp = dbds.get('m_pitch')
bbp = dbds.get('m_battpos')
llon,llat = dbds.get_xy('m_lon','m_lat')
if 1:
    pl.plot(t,d)
    pl.plot(t,wd)
    pl.plot(dd[0],dd[1])
pl.clf()
if 1:
    pl.plot(t,p,label='pitch')
    pl.plot(t,b,label='ballast')
    pl.plot(t,bp,label='battpos')
    pl.plot(t,cbp,label='commanded battpos')
    pl.plot(pp[0],pp[1],label='m_pitch')
    pl.plot(bbp[0],bbp[1],label='m_battpos')
    pl.legend()


if 1:
    pl.plot(llon,llat)
    pl.plot(lon,lat)
    pl.plot(xlon,xlat)

pl.show()
