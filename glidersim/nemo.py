import glob
from .timeconversion import strptimeToEpoch
import numpy as np
from scipy.interpolate import interp1d, interp2d
from . import getm_nc
from latlon import convertToDecimal
from . import geometry

class Cache(object):
    def __init__(self):
        self.values={}

    def clear_cache(self,fn):
        keys=[k for k in list(self.values.keys()) if k[0]==fn]
        for k in keys:
            self.values.pop(k)

    def get_cached_values(self,fn,i,j):
        key=(fn,i,j)
        if key in self.values:
            return self.values[key]
        else:
            return None
    
    def add_to_cache(self,fn,i,j,x):
        key=(fn,i,j)
        self.values[key]=x

class NemoEnvironment(object):
    NC={}
    BATHYMETRY=None
    NCBATHYMETRY='/home/lucas/working/molcard/coconet/COCONET/Mercator_bathy.nc'
    DT=86400. 
    Depth=None
    Wname='none'
    Uname='vozocrtx'
    Vname='vomecrty'
    lonname='nav_lon'
    latname='nav_lat'
    depthname='deptht'
    tempname='votemper'
    saltname='vosaline'
    bathy_lonname='none'
    bathy_latname='none'
    bathy_depthname='mbathy'
    GridDef={Uname:'U',Vname:'V',Wname:'T'}
    UseW=False
    DepthIndexFun=None

    def __init__(self,directory=None,basename='Adri_UVTS_',suffix='.nc'):
        NemoEnvironment.GridDef={NemoEnvironment.Uname:'U',
                                 NemoEnvironment.Vname:'V',
                                 NemoEnvironment.Wname:'T'}
        self.directory=directory
        self.basename=basename
        self.suffix=suffix
        self.time_offset=0.
        fns=self.__getFileList()
        startTimes=self.__getStartTimes(fns)
        self.t_min=startTimes[0]
        self.t_max=startTimes[-1]+86400.
        G=self.__getGrids(fns[0])
        self.grids={'X':tuple(G[0:2]),
                    'U':tuple(G[2:4]),
                    'V':tuple(G[4:6]),
                    'T':tuple(G[6:8])}
        self.__grid_ij=dict((k,geometry.Grid(v[0],v[1])) 
                            for k,v in self.grids.items())

        self.__netcdf_files=fns
        self.__netcdf_times=np.asarray(startTimes)
        self.__i=0
        self.__j=0
        self.cache={NemoEnvironment.Uname:Cache(),
                    NemoEnvironment.Vname:Cache(),
                    NemoEnvironment.saltname:Cache(),
                    NemoEnvironment.tempname:Cache()}
        if type(NemoEnvironment.BATHYMETRY)==type(None): 
            # load bathymetry data
            self.__setBathymetry()
            
    
    def __setBathymetry(self):
        # select a file that has bathymetry info:
        fn=NemoEnvironment.NCBATHYMETRY
        if fn==None:
            fn=self.__netcdf_files[0]
        nc=getm_nc.NcGetm(fn)
        bathymetry=nc.var(NemoEnvironment.bathy_depthname)[...]
        #lonc=nc.var(NemoEnvironment.bathy_lonname)[...]
        #latc=nc.var(NemoEnvironment.bathy_latname)[...]
        nc.close()
        # the bathymetry is in z levels. Look up in UV nc file what
        # depths correspond to that.
        nc=getm_nc.NcGetm(self.__netcdf_files[0])
        depth=nc.var('deptht')[...]
        nc.close()
        depth[0]=0
        fi=interp1d(np.arange(len(depth)),depth)
        shape=bathymetry.shape
        bathymetry_meters=fi(bathymetry.ravel()).reshape(shape)
        NemoEnvironment.BATHYMETRY=bathymetry_meters


    def __getFileList(self):
        fns=glob.glob(self.directory+'/'+self.basename+'*')
        fns.sort()
        return fns

    def __getStartTimes(self,fns):
        s=self.directory+'/'+self.basename
        d=[i.replace(s,"") for i in fns]
        d=[i.replace(self.suffix,"") for i in d]
        ts=[strptimeToEpoch(x,"%Y%m%d") for x in d]
        return ts

#
#     o  V  o
#
#     u  T  U            T is for index j,i, and so are U and V
#                        getm defines u and v for index j,i
#     o  v  o


    def __mapU(self,x):
        r=0.5*x
        #r[1:,:]+=0.5*x[:-1,:] # getm  
        r[:-1,:]+=0.5*x[1:,:]  # nema 
        return r

    def __mapV(self,x):
        r=0.5*x
        #r[:,1:]+=0.5*x[:,:-1]
        r[:,:-1]+=0.5*x[:,1:]
        return r
    
    def __mapT(self,x):
        return x

    def __getGrids(self,fn):
        nc=getm_nc.NcGetm(fn)
        x=nc.var(NemoEnvironment.lonname)[:]
        y=nc.var(NemoEnvironment.latname)[:]
        #X,Y=np.meshgrid(x,y) for rectangular grid only (as getm)
        X=x
        Y=y
        # V points
        VX=self.__mapV(X)
        VY=self.__mapV(Y)
        # U points
        UX=self.__mapU(X)
        UY=self.__mapU(Y)
        # T points
        TX=self.__mapT(X)
        TY=self.__mapT(Y)
        nc.close()
        return X,Y,UX,UY,VX,VY,TX,TY

    def __selectFile(self,t):
        ''' internal use '''
        # the time in the netcdf files seems as seconds since 00:00 of that day.
        # the first data entry however is at 3600 seconds.
        nt=np.where(self.__netcdf_times+self.time_offset<=t)[0][-1]
        # assume hourly data and one day output lengths!
        n_indices=86400./self.DT
        index=((t-self.__netcdf_times[nt]-self.time_offset)*n_indices)/86400.
        return self.__netcdf_files[nt],int(index),index-int(index)
    
    def __openNC(self,fns):
        ''' internal use. Opens a new netcdf file if current file is 
            not set or outdate. '''
        # close all outdated files:
        for ncf in list(NemoEnvironment.NC.keys()):
            if ncf not in fns:
                # remove from cache
                for cache in list(self.cache.values()):
                    cache.clear_cache(ncf)
                NemoEnvironment.NC[ncf].close()
                # and remove it:
                NemoEnvironment.NC.pop(ncf)
        # open any closed files
        for fn in fns:
            if fn not in NemoEnvironment.NC: #open it
                nc=getm_nc.NcGetm(fn)
                NemoEnvironment.NC[fn]=nc
        if NemoEnvironment.DT==None: # DT is not specified yet.
            raise ValueError("DT needs to be set by hand!")
        if NemoEnvironment.Depth==None:
            # use first fn for depth info
            NemoEnvironment.Depth=NemoEnvironment.NC[fns[0]].var(NemoEnvironment.depthname)[...]
            z=NemoEnvironment.Depth
            NemoEnvironment.DepthIndexFun=interp1d(z,np.arange(z.shape[0]),bounds_error=False)

    def __find_ij(self,lat,lon,gridname):
        ''' for a given grid (U,V,,T or D), find i,j such that lat,lon falls in
            lat[i-1,i] and lon[j-1,j]
        '''
        i,j=self.__grid_ij[gridname].find_ij(lon,lat)
        return i,j

        
        

    def __get_u(self,name,fn,index,z,lat,lon,d,eta):
        ''' reads a velocity component for given file, lat and lon. It
            returns the value interpolated to "z" 
        '''
        ugrid=self.GridDef[name]
        i,j=self.__find_ij(lat,lon,ugrid)
        if name==self.Uname:
            u=self.cache[name].get_cached_values(fn,i,j)
            if u==None:
                u=NemoEnvironment.NC[fn].var(name)[index,:,j-1:j+1,i]
                self.cache[name].add_to_cache(fn,i,j,u)
            d2=d.mean(axis=0)+eta
        elif name==self.Vname:
            u=self.cache[name].get_cached_values(fn,i,j)
            if u==None:
                u=NemoEnvironment.NC[fn].var(name)[index,:,j-1:j+1,i]
                self.cache[name].add_to_cache(fn,i,j,u)
            d2=d.mean(axis=1)+eta
        elif name==self.Wname:
            return [0.,0.]
        else:
            raise ValueError('Unknown velocity name')
        um=[None,None]
        for i in range(2):
            k=NemoEnvironment.DepthIndexFun(z)
            k=NemoEnvironment.DepthIndexFun(5) # always at 5 m depth
            if np.isnan(k) and z<10:
                k=0.
            ki=int(k)
            if np.all(~u[ki:ki+2,i].mask): # both are ok values
                f=k-ki
                x=(1-f)*u[ki,i]+f*u[ki+1,i]
            elif np.any(~u[ki:ki+2,i].mask): # only one is ok
                if u[ki+1,i].mask: # not this one but the other
                    x=u[ki,i]
                else:
                    x=u[ki+1,i]
            else:
                x=None
            um[i]=x
        if um[0]==None and um[1]!=None:
            um[0]=um[1]
        elif um[1]==None and um[0]!=None:
            um[0]=um[1]
        if um[0]==um[1]==None:
            um[0]=um[1]=0.
        return um

    def __get_ST(self,fn,index,z,lat,lon,d,eta):
        ''' Reads salinity and temperature from netcdf file. Returns
            readings averaged for the specified depth.'''
        grid=self.GridDef[self.Wname]
        k,l=self.__find_ij(lat,lon,grid)
        name=NemoEnvironment.tempname
        T=self.cache[name].get_cached_values(fn,k,l)
        if T==None:
            T=NemoEnvironment.NC[fn].var(name)[index,:,l,k]
            self.cache[name].add_to_cache(fn,k,l,T)
        name=NemoEnvironment.saltname
        S=self.cache[name].get_cached_values(fn,k,l)
        if S==None:
            S=NemoEnvironment.NC[fn].var(name)[index,:,l,k]
            self.cache[name].add_to_cache(fn,k,l,S)
        dm=NemoEnvironment.BATHYMETRY[l,k]
        idx=np.where(~S.mask)[0]
        Sm=np.interp(z,NemoEnvironment.Depth[idx],S[idx])
        Tm=np.interp(z,NemoEnvironment.Depth[idx],T[idx])
        if Sm<30:
            Q
        return Sm,Tm,dm



    def get_current_at_time(self,fn,index,lat,lon,z,k,l,d):
        ''' returns netcdf data for u, S T eta and depth for given
            lat/lon and time
        '''
        eta=0.
        u0=self.__get_u(self.Uname,fn,index,z,lat,lon,d,eta)
        lonlon=self.grids[self.GridDef[self.Uname]][0][1,k-1:k+1]
        v0=self.__get_u(self.Vname,fn,index,z,lat,lon,d,eta)
        latlat=self.grids[self.GridDef[self.Vname]][1][l-1:l+1,1]
        w0=self.__get_u(self.Wname,fn,index,z,lat,lon,d,eta)
        f=(lon-lonlon[0])/(lonlon[1]-lonlon[0])
        u0_int=u0[0]*(1-f)+u0[1]*f
        g=(lat-latlat[0])/(latlat[1]-latlat[0])
        v0_int=v0[0]*(1-g)+v0[1]*g
        S,T,D=self.__get_ST(fn,index,z,lat,lon,d,eta)
        return u0_int,v0_int,w0[0],eta,S,T,D
    
    #def get_current(self,t,lat,lon,z, convert_to_decimal=True):
    #    u=0.2
    #    v=0.2
    #    w=0.
    #    dp=118.
    #    eta=0.
    #    S=38.
    #    T=15.
    #    return u,v,w,dp,eta,S,T

    def get_current(self,t,lat,lon,z, convert_to_decimal=True):
        ''' returns netcdf data for u, S T eta and depth for given
            lat/lon and interpolated to glider time.
        '''
        #print "Setting glider depth for u to 800 m in nemo.py l.309"
        #z=800
        if t<self.t_min or t>self.t_max:
            return 0,0,0,100
        if convert_to_decimal:
            dec_lat=convertToDecimal(lat)
            dec_lon=convertToDecimal(lon)
        else:
            dec_lat=lat
            dec_lon=lon
        #
        fn,index,ft=self.__selectFile(t)
        fn1,index1,ft1=self.__selectFile(t+self.DT)
        self.__openNC([fn,fn1])
        k,l=self.__find_ij(dec_lat,dec_lon,'X')
        d=NemoEnvironment.BATHYMETRY[l-1:l+1,k-1:k+1] 
        if np.all(z>d):
            z=d.min()-5
        u0,v0,w0,eta0,S0,T0,d0=self.get_current_at_time(fn,index,dec_lat,dec_lon,z,k,l,d)
        u1,v1,w1,eta1,S1,T1,d1=self.get_current_at_time(fn1,index1,dec_lat,dec_lon,z,k,l,d)
        #
        u=u0*(1-ft)+ft*u1
        v=v0*(1-ft)+ft*v1
        w=w0*(1-ft)+ft*w1
        eta=eta0*(1-ft)+ft*eta1
        S=S0*(1-ft)+ft*S1
        T=T0*(1-ft)+ft*T1
        dp=d0*(1-ft)+ft*d1
        return u,v,w,dp,eta,S,T


if __name__=="__main__":
    ne=NemoEnvironment(directory='/home/lucas/working/molcard/coconet/COCONET')
    t0=1335916800-86400./2.
    lon=16.4
    lat=42.0

    u,v,w,dp,eta,S,T=ne.get_current(t0+86400.,lat,lon,10,False)
