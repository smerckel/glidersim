import numpy as np
import dbdreader
from scipy.optimize import fmin
from scipy.integrate import cumtrapz
import matplotlib.pyplot as plt

#dbd = dbdreader.MultiDBD(pattern = "/home/lucas/gliderdata/helgoland201407/hd/sebastian-2014-209-00-000.?bd")
dbd = dbdreader.MultiDBD(pattern="/home/lucas/gliderdata/nsb3_201907/hd/comet-2019-209-00-034.dbd")
dbd = dbdreader.MultiDBD(pattern="/home/lucas/gliderdata/nsb3_201907/hd/comet-2019-203-05-000.dbd")

t, m_fin, m_heading, m_hdg_rate, m_speed, c_fin, m_pitch, m_roll = \
    dbd.get_sync(*"m_fin m_heading m_hdg_rate m_speed c_fin m_pitch m_roll".split())

for i, delta in enumerate(np.diff(m_heading)):
    if delta<-np.pi:
        m_heading[i+1:]+=np.pi*2
    elif delta > np.pi:
        m_heading[i+1:]-=np.pi*2

m_speed /= np.cos(m_pitch)

mavg = lambda x : np.convolve(x, np.ones(15)/15, 'same')

dot_m_hdg_rate = mavg(np.gradient(m_hdg_rate)/np.gradient(t))

F = mavg(np.sin(m_fin) * m_speed**2)
omega = mavg(np.gradient(m_heading)/np.gradient(t))


condition = np.logical_and(np.abs(F)<0.04, np.abs(omega)<0.15)
condition = np.logical_and(condition, np.isfinite(m_speed))
x,y,z,r, tm = np.compress(condition, (F, omega, dot_m_hdg_rate, m_roll, t), axis=1)

idx = np.where(np.isnan(m_speed))[0]
m_speed[idx] = 0.
tau=15
x2 = np.interp(tm, tm+tau, x)
A, B = np.polyfit(x2, y, 1)
F = mavg(np.sin(m_fin) * m_speed**2)
A*=1.4
#A=0.55

omega_p = np.zeros_like(F)
dt = np.diff(t)
for i, _omega in enumerate(m_hdg_rate):
    if i==0:
        continue
    else:
        #omega_p[i] = (A*F[i]/tau - 1/tau * omega_p[i-1])*dt[i-1] + omega_p[i-1]
        omega_p[i] = A*F[i]/tau*dt[i-1] + omega_p[i-1]*(1-dt[i-1]/2/tau)
        omega_p[i] /= 1+dt[i-1]/2/tau
plt.plot(t, omega, label='measured')
plt.plot(t, omega_p, label='modelled')
#plt.xlim(1406618498, 1406621504)
plt.ylim(-0.2, 0.2)
plt.legend()
