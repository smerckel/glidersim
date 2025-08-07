import os
import pickle
import glob
import numpy as np

from latlon import convertToDecimal
from GliderNetCDF import ncHereon

class Data(object):
    def __init__(self,gs={},period=10):
        self.gs=gs
        self.data=dict((k,[]) for k in list(gs.keys()))
        self.__cnt=0
        self.period=period

    def __save_pickle(self,fn):
        with open(fn,'wb') as fd:
            pickle.dump(self.data,fd)

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

    def __save_nc(self, fn):
        k_tm = "m_present_time"
        k_ignore = ["utm_0"]
        tm = self.data[k_tm]
        opts = dict(title="Results of glidersim model",
                    source="n.a.",
                    originator="n.a.")
                    
        with ncHereon(fn, mode='w', **opts) as nc:
            for k in self.data.keys():
                if k==k_tm:
                    continue
                if k in k_ignore:
                    continue
                nc.add_parameter(k,'-', tm, self.data[k])
                
        
    def __load_pickle(self,fn):
        with open(fn,'rb') as fd:
            self.data=pickle.load(fd)

    def create_new_filename(self, fn, suffix):
        directory, filename = os.path.split(fn)
        root, ext = os.path.splitext(filename)
        abs_root = os.path.join(directory, f"{root}_")
        fns = glob.glob(f"{abs_root}*{ext}")
        fns.sort()
        if fns:
            most_recent_fn = fns[-1]
            most_recent_suffix = most_recent_fn.replace(abs_root,"").replace(ext,"")
            index = int(most_recent_suffix)
            s = f"{{:{suffix}}}".format(index)
            assert s == most_recent_suffix
        else:
            index = -1
        s = f"{{:{suffix}}}".format(index+1)
        fn = f"{abs_root}{s}{ext}"
        return fn

    def save(self,fn=None,data_format=None, filename_suffix=None):
        ''' 
        filename_suffix: str or None
            If not None, defines how the filename is modified. For example "03d"
        '''
        fn = fn or self.output
        if filename_suffix:
            fn = self.create_new_filename(fn, filename_suffix)
        print(f"Writing output to {fn}...")
        _, extension = os.path.splitext(fn)
        s = extension.lower()[1:]
        data_format = data_format or s
        if data_format == 'pck':
            self.__save_pickle(fn)
        elif data_format == 'nc':
            self.__save_nc(fn)
        elif data_format in ['asc', 'txt']:
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
    
