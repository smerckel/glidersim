import math
from latlonUTM import UTM2latlon
from latlon import convertToNmea, convertToDecimal
from . import getm_nc
import glob
import numpy as np
from scipy.interpolate import interp2d
from .timeconversion import strptimeToEpoch
import os

import random

class Bathymetry(object):
    NCBATHYMETRY='/home/lucas/getm_data/kofserver2/bathymetry.nc'
    BATHYMETRY=None

    def __init__(self,bathymetry_filename=None,
                 latitude_variable_name="latc",
                 longitude_variable_name="lonc",
                 bathymetry_variable_name="bathymetry"):
        if bathymetry_filename==None:
            bathymetry_filename=Bathymetry.NCBATHYMETRY
        self.latitude=latitude_variable_name
        self.longitude=longitude_variable_name
        self.bathymetry=bathymetry_variable_name
        G=self.__getGrids(bathymetry_filename)
        self.grids={'X':tuple(G[0:2])}
        self.__grid_ij=dict((k,[0,0]) for k in list(self.grids.keys()))
        self.__setBathymetry(bathymetry_filename)

    def __transform_bathymetry_data(self,latc,lonc,bathymetry):
        lat=self.grids['X'][1][:,0]
        lon=self.grids['X'][0][0,:]
        # the grid of the new nc files are slightly smaller than the geometry grid.
        # lon[10:] and lat[1:-16] should be used. Check if there are no differences:
        if abs((lonc[10:]-lon).sum())<1e-5 and \
                abs((latc[1:-15]-lat).sum())<1e-5:
            Bathymetry.BATHYMETRY=bathymetry[1:-15,10:]
        else:
            raise ValueError("Don't know how to get the bathymetry. Shapes don't match.")
    
    def __setBathymetry(self,fn):
        # select a file that has bathymetry info:
        nc=getm_nc.NcGetm(fn)
        bathymetry=nc.var(self.bathymetry)[...]
        lonc=nc.var(self.longitude)[...]
        latc=nc.var(self.latitude)[...]
        self.increment_latitude=int(np.all(np.diff(latc)>0))*2-1
        self.increment_longitude=int(np.all(np.diff(lonc)>0))*2-1
        nc.close()
        Bathymetry.BATHYMETRY=bathymetry[...]
        #self.__transform_bathymetry_data(latc,lonc,bathymetry)

    def __find_ij(self,lat,lon,gridname):
        ''' for a given grid (U,V,,T or D), find i,j such that lat,lon falls in
            lat[i-1,i] and lon[j-1,j]
        '''
        grid=self.grids[gridname]
        i,j=self.__grid_ij[gridname]
        lats=grid[1][:,-1]
        lons=grid[0][-1,:]
        while 1:
            if lat<=lats[j] and lat>lats[j-self.increment_latitude]:
                break
            if lats[j]>lat:j-=self.increment_latitude
            if lats[j]<lat:j+=self.increment_latitude
        while 1:
            if lon<=lons[i] and lon>lons[i-self.increment_longitude]:
                break
            if lons[i]>lon:i-=self.increment_longitude
            if lons[i]<lon:i+=self.increment_longitude
        self.__grid_ij[gridname]=[i,j]
        return i,j

    def __getGrids(self,fn):
        nc=getm_nc.NcGetm(fn)
        x=nc.var(self.longitude)[:]
        y=nc.var(self.latitude)[:]
        X,Y=np.meshgrid(x,y)
        nc.close()
        return X,Y

    def get_water_depth(self,lat,lon):
        ''' returns water depth for given lat/lon (in decimal notation).
        '''
        k,l=self.__find_ij(lat,lon,'X')
        d=Bathymetry.BATHYMETRY[l-1:l+1,k-1:k+1]
        k,l=self.__find_ij(lat,lon,'X')
        lons=self.grids['X'][0][l-1:l+1,k-1:k+1]
        lats=self.grids['X'][1][l-1:l+1,k-1:k+1]
        f=(lon-lons[0][0])/(lons[0][1]-lons[0][0])
        g=(lat-lats[0][0])/(lats[1][0]-lats[0][0])
        dm=d[0,0]*(1-f)*(1-g)+d[1,0]*(1-f)*g+d[0,1]*f*(1-g)+d[1,1]*f*g
        return dm


class GetmEnvironment(object):
    CurrentFile=None
    NC=None
    SIGMA=None
    NSIGMA=None
    NSIGMALEVELS=None
    BATHYMETRY=None
    NCBATHYMETRY='/home/lucas/getm_data/getm3d/bathymetry.nc'
    DT=None
    #Uname='eastward_sea_water_velocity'
    #Vname='northward_sea_water_velocity'
    Wname='w'
    Uname='uu'
    Vname='vv'
    GridDef={Uname:'U',Vname:'V',Wname:'T'}
    UseW=True
    CurrentScaleFactor={'U':(1.,0.),
                        'V':(1.,0.),
                        'T':(1.,0.)}

    def __init__(self,directory=None,basename='netcdf',suffix='GETM.nc'):
        GetmEnvironment.GridDef={GetmEnvironment.Uname:'U',
                                 GetmEnvironment.Vname:'V',
                                 GetmEnvironment.Wname:'T'}
        self.directory=directory
        #self.basename='getm3d_'
        #self.suffix=".nc"
        #self.time_offset=1 # hour offset as time starts at 11 pm previous day.
        self.basename=basename
        self.suffix=suffix
        self.time_offset=3600. # time starts at 00:00 of the day of the file
                               # but the first entry is at 3600 seconds.
        fns=self.__getFileList()
        startTimes=self.__getStartTimes(fns)
        self.t_min=startTimes[0]
        self.t_max=startTimes[-1]+86400.
        G=self.__getGrids(fns[0])
        self.grids={'X':tuple(G[0:2]),
                    'U':tuple(G[2:4]),
                    'V':tuple(G[4:6]),
                    'T':tuple(G[6:8])}
        self.__grid_ij=dict((k,[0,0]) for k in list(self.grids.keys()))

        if type(GetmEnvironment.BATHYMETRY)==type(None): 
            # load bathymetry data
            self.__setBathymetry()
        self.__netcdf_files=fns
        self.__netcdf_times=np.asarray(startTimes)
        self.__i=0
        self.__j=0

    def __transform_bathymetry_data(self,latc,lonc,bathymetry):
        lat=self.grids['X'][1][:,0]
        lon=self.grids['X'][0][0,:]
        # the grid of the new nc files are slightly smaller than the geometry grid.
        # lon[10:] and lat[1:-16] should be used. Check if there are no differences:
        if abs((lonc[10:]-lon).sum())<1e-5 and \
                abs((latc[1:-15]-lat).sum())<1e-5:
            GetmEnvironment.BATHYMETRY=bathymetry[1:-15,10:]
        else:
            raise ValueError("Don't know how to get the bathymetry. Shapes don't match.")
    
    def __setBathymetry(self):
        # select a file that has bathymetry info:
        fn=GetmEnvironment.NCBATHYMETRY
        nc=getm_nc.NcGetm(fn)
        GetmEnvironment.BATHYMETRY=nc.var('bathymetry')[...]
        #lonc=nc.var('lonc')[...]
        #latc=nc.var('latc')[...]
        nc.close()
        #self.__transform_bathymetry_data(latc,lonc,bathymetry)

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

    def __mapU(self,x):
        r=0.5*x
        r[1:,:]+=0.5*x[:-1,:]
        return r

    def __mapV(self,x):
        r=0.5*x
        r[:,1:]+=0.5*x[:,:-1]
        return r
    
    def __mapT(self,x):
        r=0.25*x
        r[:,1:]+=0.25*x[:,:-1]
        r[1:,:]+=0.25*x[:-1,:]
        r[1:,1:]+=0.25*x[:-1,:-1]
        return r

    def __getGrids(self,fn):
        nc=getm_nc.NcGetm(fn)
        x=nc.var('lonc')[:]
        y=nc.var('latc')[:]
        X,Y=np.meshgrid(x,y)
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
        index=((t-self.__netcdf_times[nt]-self.time_offset)*24)/86400.
        return self.__netcdf_files[nt],int(index),index-int(index)
    
    def __openNC(self,fn):
        ''' internal use. Opens a new netcdf file if current file is 
            not set or outdate. '''
        if GetmEnvironment.CurrentFile!=fn:
            if GetmEnvironment.CurrentFile:
                GetmEnvironment.NC.close()
            GetmEnvironment.CurrentFile=fn
            GetmEnvironment.NC=getm_nc.NcGetm(fn)
            GetmEnvironment.SIGMA=GetmEnvironment.NC.var('sigma')[:]
            GetmEnvironment.NSIGMA=np.arange(len(GetmEnvironment.SIGMA),0.,-1,dtype=float)-1
            GetmEnvironment.NSIGMALEVELS=len(GetmEnvironment.SIGMA)
        if GetmEnvironment.DT==None: # DT is not specified yet.
            GetmEnvironment.DT=np.diff(GetmEnvironment.NC.var('time')[...])[0]
            
    def __find_ij(self,lat,lon,gridname):
        ''' for a given grid (U,V,,T or D), find i,j such that lat,lon falls in
            lat[i-1,i] and lon[j-1,j]
        '''
        grid=self.grids[gridname]
        i,j=self.__grid_ij[gridname]
        lats=grid[1][:,-1]
        lons=grid[0][-1,:]
        while 1:
            if lat<=lats[j] and lat>lats[j-1]:
                break
            if lats[j]>lat:j-=1
            if lats[j]<lat:j+=1
        while 1:
            if lon<=lons[i] and lon>lons[i-1]:
                break
            if lons[i]>lon:i-=1
            if lons[i]<lon:i+=1
        self.__grid_ij[gridname]=[i,j]
        return i,j

        
        

    def __get_u(self,name,fn,index,z,lat,lon,d,eta):
        ''' reads a velocity component for given file, lat and lon. It
            returns the value interpolated to "z" 
        '''
        ugrid=self.GridDef[name]
        a,b=self.CurrentScaleFactor[ugrid]
        i,j=self.__find_ij(lat,lon,ugrid)
        if name==self.Uname:
            u=GetmEnvironment.NC.var(name)[index,:,j,i-1:i+1]
            d2=d.mean(axis=0)+eta
        elif name==self.Vname:
            u=GetmEnvironment.NC.var(name)[index,:,j-1:j+1,i]
            d2=d.mean(axis=1)+eta
        elif name==self.Wname:
            if GetmEnvironment.UseW:
                u=GetmEnvironment.NC.var(name)[index,:,j,i:i+1]
            else:
                u=np.zeros((GetmEnvironment.NSIGMALEVELS,2),float)
            d2=[d.mean()+eta]
        else:
            raise ValueError('Unknown velocity name')
        um=[]
        for d_i,u_i in zip(d2,u.T):
            if u_i[0]<-100:
                u_i[0]=0.
            x=np.interp(z,d_i*(1.-GetmEnvironment.NSIGMA/GetmEnvironment.NSIGMALEVELS),u_i[::-1])
            um.append(a*x+b) # scaling the velocity component
        return um

    def __get_ST(self,fn,index,z,lat,lon,d,eta):
        ''' Reads salinity and temperature from netcdf file. Returns
            readings averaged for the specified depth.'''
        grid=self.GridDef['w']
        k,l=self.__find_ij(lat,lon,grid)
        T=GetmEnvironment.NC.var('temp')[index,:,l-1:l+1,k-1:k+1]
        S=GetmEnvironment.NC.var('salt')[index,:,l-1:l+1,k-1:k+1]
        T4=np.zeros((2,2),float)
        S4=np.zeros((2,2),float)
        for i in range(2):
            for j in range(2):
                x=np.interp(z,d[j,i]*(1.-GetmEnvironment.NSIGMA/GetmEnvironment.NSIGMALEVELS),T[::-1,j,i])
                y=np.interp(z,d[j,i]*(1.-GetmEnvironment.NSIGMA/GetmEnvironment.NSIGMALEVELS),S[::-1,j,i])
                if x>0:
                    T4[j,i]=x
                    S4[j,i]=y
                else:
                    idx=np.where(T[:,j,i].data>0)[0]
                    if len(idx)>0:
                        T4[j,i]=T[idx[0],j,i]
                        S4[j,i]=S[idx[0],j,i]
        if np.any(S4<=0):
            if not np.all(S4<=0):
                # at least one of the points is on land, but not all
                idx,jdx=np.where(S4>0)
                S4=np.ones((2,2),float)*(S4[idx,jdx]).mean()
                T4=np.ones((2,2),float)*(T4[idx,jdx]).mean()
            else:
                S4=np.ones((2,2),float)*15.
                T4=np.ones((2,2),float)*15.
                raise GliderException("Stranded")
            
        lons=self.grids['T'][0][l-1:l+1,k-1:k+1]
        lats=self.grids['T'][1][l-1:l+1,k-1:k+1]
        f=(lon-lons[0][0])/(lons[0][1]-lons[0][0])
        g=(lat-lats[0][0])/(lats[1][0]-lats[0][0])
        Tm=T4[0,0]*(1-f)*(1-g)+T4[1,0]*(1-f)*g+T4[0,1]*f*(1-g)+T4[1,1]*f*g
        Sm=S4[0,0]*(1-f)*(1-g)+S4[1,0]*(1-f)*g+S4[0,1]*f*(1-g)+S4[1,1]*f*g

        k,l=self.__find_ij(lat,lon,'X')
        lons=self.grids['X'][0][l-1:l+1,k-1:k+1]
        lats=self.grids['X'][1][l-1:l+1,k-1:k+1]
        f=(lon-lons[0][0])/(lons[0][1]-lons[0][0])
        g=(lat-lats[0][0])/(lats[1][0]-lats[0][0])
        dm=d[0,0]*(1-f)*(1-g)+d[1,0]*(1-f)*g+d[0,1]*f*(1-g)+d[1,1]*f*g
        return Sm,Tm,dm



    def get_current_at_time(self,fn,index,lat,lon,z,k,l,d):
        ''' returns netcdf data for u, S T eta and depth for given
            lat/lon and time
        '''
        eta=GetmEnvironment.NC.var('elev')[index,l-1:l+1,k-1:k+1].mean()
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
    
    def get_current(self,t,lat,lon,z, convert_to_decimal=True):
        ''' returns netcdf data for u, S T eta and depth for given
            lat/lon and interpolated to glider time.
        '''
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
        self.__openNC(fn)
        k,l=self.__find_ij(dec_lat,dec_lon,'X')
        d=GetmEnvironment.BATHYMETRY[l-1:l+1,k-1:k+1] 
        u0,v0,w0,eta0,S0,T0,d0=self.get_current_at_time(fn,index,dec_lat,dec_lon,z,k,l,d)
        #
        fn1,index1,ft1=self.__selectFile(t+self.DT)
        self.__openNC(fn1)
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
        

class GetmEnvironmentInterpolated(GetmEnvironment):
    def __init__(self,directory=None,basename='netcdf',suffix='GETM.nc'):
        ''' assumes all values are interpolated onto the same grid.'''
        GetmEnvironment.__init__(self,directory,basename,suffix)
        fns=self._GetmEnvironment__getFileList()
        G=self._GetmEnvironment__getGrids(fns[0])
        self.grids={'X':tuple(G[0:2]),
                    'U':tuple(G[0:2]),
                    'V':tuple(G[0:2]),
                    'T':tuple(G[0:2])}
        self.__grid_ij=dict((k,[0,0]) for k in list(self.grids.keys()))

############################################


class GetmEnvironment2D(object):
    CurrentFile=None
    NC=None
    DT=None
    Uname='uu'
    Vname='vv'
    Tname='sst'
    Sname='sss'

    def __init__(self,directory=None,basename='netcdf',suffix='GETM.nc'):
        GetmEnvironment2D.GridDef={GetmEnvironment2D.Uname:'U',
                                   GetmEnvironment2D.Vname:'V'}
        self.directory=directory
        self.basename=basename
        self.suffix=suffix
        self.time_offset=3600. # time starts at 00:00 of the day of the file
                               # but the first entry is at 3600 seconds.
        fns=self.__getFileList()
        startTimes=self.__getStartTimes(fns)
        self.t_min=startTimes[0]
        self.t_max=startTimes[-1]+86400.
        G=self.__getGrids(fns[0])
        self.grids={'X':tuple(G[0:2]),
                    'U':tuple(G[2:4]),
                    'V':tuple(G[4:6]),
                    'T':tuple(G[6:8])}
        self.__grid_ij=dict((k,[0,0]) for k in list(self.grids.keys()))

        #if GetmEnvironment.BATHYMETRY==None: 
        #    # load bathymetry data
        #    self.__setBathymetry()
        self.__netcdf_files=fns
        self.__netcdf_times=np.asarray(startTimes)
        self.__i=0
        self.__j=0

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

    def __mapU(self,x):
        r=0.5*x
        r[1:,:]+=0.5*x[:-1,:]
        return r

    def __mapV(self,x):
        r=0.5*x
        r[:,1:]+=0.5*x[:,:-1]
        return r
    
    def __mapT(self,x):
        r=0.25*x
        r[:,1:]+=0.25*x[:,:-1]
        r[1:,:]+=0.25*x[:-1,:]
        r[1:,1:]+=0.25*x[:-1,:-1]
        return r

    def __getGrids(self,fn):
        nc=getm_nc.NcGetm(fn)
        x=nc.var('lonc')[:]
        y=nc.var('latc')[:]
        X,Y=np.meshgrid(x,y)
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
        index=((t-self.__netcdf_times[nt]-self.time_offset)*24)/86400.
        return self.__netcdf_files[nt],int(index),index-int(index)
    
    def __openNC(self,fn):
        ''' internal use. Opens a new netcdf file if current file is 
            not set or outdate. '''
        if GetmEnvironment2D.CurrentFile!=fn:
            if GetmEnvironment2D.CurrentFile:
                GetmEnvironment2D.NC.close()
            GetmEnvironment2D.CurrentFile=fn
            GetmEnvironment2D.NC=getm_nc.NcGetm(fn)
        if GetmEnvironment2D.DT==None: # DT is not specified yet.
            GetmEnvironment2D.DT=np.diff(GetmEnvironment2D.NC.var('time')[...])[0]
            
    def __find_ij(self,lat,lon,gridname):
        ''' for a given grid (U,V,,T or D), find i,j such that lat,lon falls in
            lat[i-1,i] and lon[j-1,j]
        '''
        grid=self.grids[gridname]
        i,j=self.__grid_ij[gridname]
        lats=grid[1][:,-1]
        lons=grid[0][-1,:]
        while 1:
            if lat<=lats[j] and lat>lats[j-1]:
                break
            if lats[j]>lat:j-=1
            if lats[j]<lat:j+=1
        while 1:
            if lon<=lons[i] and lon>lons[i-1]:
                break
            if lons[i]>lon:i-=1
            if lons[i]<lon:i+=1
        self.__grid_ij[gridname]=[i,j]
        return i,j


    def __get_u(self,name,fn,index,lat,lon):
        ''' reads a velocity component for given file, lat and lon. It
            returns the value interpolated to "z" 
        '''
        ugrid=self.GridDef[name]
        i,j=self.__find_ij(lat,lon,ugrid)
        if name==self.Uname:
            u=GetmEnvironment2D.NC.var(name)[index,j,i-1:i+1]
        elif name==self.Vname:
            u=GetmEnvironment2D.NC.var(name)[index,j-1:j+1,i]
        else:
            raise ValueError('Unknown velocity name')
        return u

    def __get_ST(self,fn,index,lat,lon):
        ''' Reads salinity and temperature from netcdf file. Returns
            readings averaged for the specified depth.'''
        grid='U' # all grids should be the same.
        k,l=self.__find_ij(lat,lon,grid)
        T4=GetmEnvironment2D.NC.var(self.Tname)[index,l-1:l+1,k-1:k+1]
        S4=GetmEnvironment2D.NC.var(self.Sname)[index,l-1:l+1,k-1:k+1]
        lons=self.grids['T'][0][l-1:l+1,k-1:k+1]
        lats=self.grids['T'][1][l-1:l+1,k-1:k+1]
        f=(lon-lons[0][0])/(lons[0][1]-lons[0][0])
        g=(lat-lats[0][0])/(lats[1][0]-lats[0][0])
        Tm=T4[0,0]*(1-f)*(1-g)+T4[1,0]*(1-f)*g+T4[0,1]*f*(1-g)+T4[1,1]*f*g
        Sm=S4[0,0]*(1-f)*(1-g)+S4[1,0]*(1-f)*g+S4[0,1]*f*(1-g)+S4[1,1]*f*g
        return Sm,Tm

    def get_current_at_time(self,fn,index,lat,lon,k,l):
        ''' returns netcdf data for u, S T eta and depth for given
            lat/lon and time
        '''
        eta=GetmEnvironment2D.NC.var('elev')[index,l-1:l+1,k-1:k+1].mean()
        u0=self.__get_u(self.Uname,fn,index,lat,lon)
        lonlon=self.grids[self.GridDef[self.Uname]][0][1,k-1:k+1]
        v0=self.__get_u(self.Vname,fn,index,lat,lon)
        latlat=self.grids[self.GridDef[self.Vname]][1][l-1:l+1,1]
        f=(lon-lonlon[0])/(lonlon[1]-lonlon[0])
        u0_int=u0[0]*(1-f)+u0[1]*f
        g=(lat-latlat[0])/(latlat[1]-latlat[0])
        v0_int=v0[0]*(1-g)+v0[1]*g
        S,T=self.__get_ST(fn,index,lat,lon)
        return u0_int,v0_int,eta,S,T
    
    def get_current(self,t,lat,lon,z,convert_to_decimal=True):
        ''' returns netcdf data for u, S T eta and depth for given
            lat/lon and interpolated to glider time.
            z is not used.
        '''
        if t<self.t_min or t>self.t_max:
            raise ValueError("Can't find the time. No nc file of requested time is present?")
        if convert_to_decimal:
            dec_lat=convertToDecimal(lat)
            dec_lon=convertToDecimal(lon)
        else:
            dec_lat=lat
            dec_lon=lon
        #
        
        fn,index,ft=self.__selectFile(t)
        self.__openNC(fn)
        k,l=self.__find_ij(dec_lat,dec_lon,'X')
        u0,v0,eta0,S0,T0=self.get_current_at_time(fn,index,dec_lat,dec_lon,k,l)
        #
        fn1,index1,ft1=self.__selectFile(t+self.DT)
        self.__openNC(fn1)
        u1,v1,eta1,S1,T1=self.get_current_at_time(fn1,index1,dec_lat,dec_lon,k,l)
        #
        u=u0*(1-ft)+ft*u1
        v=v0*(1-ft)+ft*v1
        S=S0*(1-ft)+ft*S1
        T=T0*(1-ft)+ft*T1
        eta=eta0*(1-ft)+ft*eta1
        return u,v,0,0,eta,S,T


class GetmEnvironment2DInterpolated(GetmEnvironment2D):
    def __init__(self,directory=None,basename='netcdf',suffix='GETM.nc'):
        ''' assumes all values are interpolated onto the same grid.'''
        GetmEnvironment2D.__init__(self,directory,basename,suffix)
        fns=self._GetmEnvironment2D__getFileList()
        G=self._GetmEnvironment2D__getGrids(fns[0])
        self.grids={'X':tuple(G[0:2]),
                    'U':tuple(G[0:2]),
                    'V':tuple(G[0:2]),
                    'T':tuple(G[0:2])}
        self.__grid_ij=dict((k,[0,0]) for k in list(self.grids.keys()))


#########################################

if __name__=="__main__":
    GetmEnvironment2D.Uname="surface_eastward_sea_water_velocity"
    GetmEnvironment2D.Vname="surface_northward_sea_water_velocity"
    G=GetmEnvironment2D(directory="/home/lucas/samba/cosyna/netcdf/PO-Flow/gb_1km",
                        basename="getm2d_",
                        suffix=".nc")
    t=strptimeToEpoch("5 Jul 2013 12:00","%d %b %Y %H:%M")
    
