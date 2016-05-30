import numpy as np
from latlon import convertToDecimal
import pickle

class Data(object):
    def __init__(self,gs={},period=10):
        self.gs=gs
        self.data=dict((k,[]) for k in list(gs.keys()))
        self.__cnt=0
        self.period=period

    def __save_pickle(self,fn):
        fd=open(fn,'w')
        pickle.dump(self.data,fd)
        fd.close()

    def __save_ascii(self,fn):
        fd=open(fn,'w')
        # print header
        keys=list(self.data.keys())
        hdr="#"+" ".join(keys)+"\n"
        fd.write(hdr)
        n=len(self.data[keys[0]])
        for i in range(n):
            s=" ".join(["%s"%(self.data[k][i].__str__()) for k in keys])
            fd.write(s+"\n")
        fd.close()
        
        
    def __load_pickle(self,fn):
        fd=open(fn,'r')
        self.data=pickle.load(fd)
        fd.close()

    def save(self,fn=None,data_format='pickle'):
        ''' '''
        if fn==None:
            fn=self.output
        if data_format=='pickle':
            self.__save_pickle(fn)
        else:
            self.__save_ascii(fn)

    def get(self,parameter):
        return np.array(self.data[parameter])

    def load(self,fn,data_format='pickle'):
        if data_format=='pickle':
            self.__load_pickle(fn)

    def add_data(self,force_data_write=False):
        self.__cnt+=1
        if self.__cnt==self.period or force_data_write:
            self.__cnt=0
            for k,v in self.gs.items():
                self.data[k].append(v)
    
