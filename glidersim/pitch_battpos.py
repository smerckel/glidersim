import numpy as np
import utils.regression as r

data=np.loadtxt('pitch-battpos-data.txt')
ballast=data.T[0]
b=data.T[1]
Vp=ballast*1e-6 # m^3
x2=Vp**2
x1=Vp

x=np.vstack([x1,x2,np.ones(x1.shape)])
s=r.regression(x,b)
