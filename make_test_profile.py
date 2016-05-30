import numpy as np
import gsw
import dbdreader
import ndf


dbd=dbdreader.DBD("/home/lucas/gliderdata/toulon_201504/hd/comet-2015-098-03-000.ebd")

tmp=dbd.get_sync("sci_ctd41cp_timestamp",["sci_water_temp","sci_water_cond","sci_water_pressure"])

t,tctd,T,C,P=np.compress(tmp[2]>0,tmp,axis=1)

SP=gsw.SP_from_C(C*10,T,P*10)
SA=gsw.SA_from_SP(SP,P*10,43.1,4.8)
CT=gsw.CT_from_t(SA,T,P*10)
rho=gsw.rho(SA,CT,P*10)
i=np.argsort(rho)
z_s=P[i]*10
rho_is=rho[i]
zi=np.arange(0,P.max()*10,2)
rhoi=np.interp(zi,z_s,rho_is)

data=ndf.NDF()
data.add_parameter("rho","kg/m^3",(zi,rhoi),"in situ density toulon exp.")
data.save("toulon/density_profile_toulon.ndf")
