import netCDF4


class NcGetm(object):
    CACHE={}
    def __init__(self,filename):
        self.filename=filename
        try:
            self.nc=netCDF4.Dataset(filename,mode="r")
            print("loaded {0}...".format(filename))
        except RuntimeError as e:
            if "No such file or directory" in e.args:
                raise IOError("%s not found."%(filename))
            else:
                raise RuntimeError(e)
            
        #dimensions=self.nc.dimensions
        #for k,v in dimensions.iteritems():
        #    self.__dict__[k]=v
        self.dimensions=list(self.nc.dimensions.keys())
        self.variables=list(self.nc.variables.keys())

    def var(self,variable):
        ''' returns a netcdf variable, which returns values when sliced. I.e., if you
            want all variables, slice it as 
            x=nc.var('U')
            x[...] 
            #or 
            x[:]
        '''
        return self.nc.variables[variable]
    
    def get(self,variable):
        x=self.var(variable)
        if hasattr(x,'scale_factor'):
            f=x.scale_factor
        else:
            f=1.
        if hasattr(x,'add_offset'):
            b=x.add_offset
        else:
            b=0.
        return f,b,x


    def cachedvar(self,variable):
        ''' returns a netcdf variable, which returns values when sliced. I.e., if you
            want all variables, slice it as 
            x=nc.var('U')
            x[...] 
            #or 
            x[:]
        '''
        key=(self.filename,variable)
        if key not in NcGetm.CACHE:
            NcGetm.CACHE[key]=self.nc.variables[variable]
        return NcGetm.CACHE[key]


    def close(self):
        self.nc.close()

if __name__=='__main__':
    nc=NcGetm('/home/lucas/getm_data/kofserver2/getm3d_20111014.nc')
