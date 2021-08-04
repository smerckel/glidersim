import numpy as np
import dbdreader
from scipy.optimize import fmin
from scipy.integrate import cumtrapz
import matplotlib.pyplot as plt

dbd = dbdreader.MultiDBD(pattern = "/home/lucas/gliderdata/helgoland201407/hd/sebastian-2014-209-00-000.?bd")

t, m_fin, m_heading, m_hdg_rate, m_speed, c_heading, c_fin, m_pitch, m_roll = \
    dbd.get_sync(*"m_fin m_heading m_hdg_rate m_speed c_heading c_fin m_pitch m_roll".split())


m_speed /= np.cos(m_pitch)

mavg = lambda x : np.convolve(x, np.ones(5)/5, 'same')


F = np.sin(m_fin) * m_speed**2
dot_m_hdg_rate = mavg(np.gradient(m_hdg_rate)/np.gradient(t))
omega = mavg(m_hdg_rate)

condition = np.logical_and(np.abs(F)<0.04, np.abs(omega)<0.15)
x,y,z,r, tm = np.compress(condition, (F, omega, dot_m_hdg_rate, m_roll, t), axis=1)
x2 = np.interp(tm, tm+10, x)

A, B = np.polyfit(x2, y, 1)
tau = 10.
C=0.
A*=2
omega_p = np.zeros_like(F)
dt = np.diff(t)
for i, _omega in enumerate(m_hdg_rate):
    if i==0:
        continue
    else:
        omega_p[i] = A/2*(F[i]+F[i-1]) - 0.5 * omega_p[i-1] + tau/dt[i-1]*omega_p[i-1]
        omega_p[i] += C/2*(m_roll[i] + m_roll[i-1])
        omega_p[i] /= tau/dt[i-1] + 0.5

plt.plot(t, omega, label='measured')
plt.plot(t, omega_p, label='modelled')
plt.xlim(1406618498, 1406621504)
plt.ylim(-0.2, 0.2)
plt.legend()
