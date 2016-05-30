import numpy as np

class Triangle(object):
    def __init__(self):
        self.x=[]
        self.y=[]
        
    def set_xy(self,x,y):
        self.x=x
        self.y=y
    
    def contains(self,x,y):
        det=(self.x[0]-self.x[2])*(self.y[1]-self.y[2])
        det-=(self.y[0]-self.y[2])*(self.x[1]-self.x[2])
        
        l=[((self.y[1]-self.y[2])*(x-self.x[2])+(self.x[2]-self.x[1])*(y-self.y[2]))/det]
        l.append(((self.y[2]-self.y[0])*(x-self.x[2])+
                  (self.x[0]-self.x[2])*(y-self.y[2]))/det)
        l.append(1-l[0]-l[1])
        r=True
        for _l in l:
            r&=_l>=0
            r&=_l<=1
        return r

class Rectangle(object):
    def __init__(self):
        self.x=[]
        self.y=[]
        self.triangles=[Triangle() for i in range(2)]

    def set_xy(self,x,y):
        self.x=x
        self.y=y
        self.x.append(self.x[0])
        self.y.append(self.y[0])

    def contains(self,x,y):
        self.triangles[0].set_xy(self.x[:3],self.y[:3])
        self.triangles[1].set_xy(self.x[2:],self.y[2:])
        r=self.triangles[0].contains(x,y) or \
            self.triangles[1].contains(x,y)
        return r

    def center(self):
        x=sum(self.x[:-1])/4.
        y=sum(self.y[:-1])/4.
        return x,y

    def minmax(self):
        return min(self.x),max(self.x),min(self.y),max(self.y)

class Grid(object):
    def __init__(self,x,y):
        self.nx,self.ny=x.shape
        self.nx-=1
        self.ny-=1
        self.grid=self.fill_grid(x,y)
        self.i=self.nx/2
        self.j=self.ny/2
        

    def fill_grid(self,x,y):
        R=[]
        for i in range(self.ny):
            for j in range(self.nx):
                r=Rectangle()
                r.set_xy([x[j,i],
                          x[j+1,i],
                          x[j+1,i+1],
                          x[j,i+1]],
                         [y[j,i],
                          y[j+1,i],
                          y[j+1,i+1],
                          y[j,i+1]])
                R.append(r)
        return np.array(R).reshape((self.ny,self.nx))

    def find_ij(self,x,y):
        i=self.i
        j=self.j
        k=0
        while 1:
            if self.grid[i,j].contains(x,y):
                break
            minx,maxx,miny,maxy=self.grid[i,j].minmax()
            moved=False
            if x<minx:i-=1; moved=True
            if x>maxx:i+=1; moved=True
            if y<miny:j-=1; moved=True
            if y>maxy:j+=1; moved=True
            if not moved:
                found=False
                for ii in range(3):
                    for jj in range(3):
                        found|=self.grid[i+ii-1,j+jj-1].contains(x,y)
                if found:
                     break
            if k>100:
                raise ValueError('Max iterations exceeded.')
            k+=1
            if k>25:
                print("(geometry.py) iteration: %d i:%d j:%d x:%f y:%f"%(k,i,j,x,y))
        self.i=i
        self.j=j
        return i,j
            

if __name__=="__main__":
    T=Triangle()
    xs=[0,2,3]
    ys=[0,0,3]
    T.set_xy(xs,ys)
    print(T.contains(1,0.2))
    print(T.contains(1,-0.5))
    R=Rectangle()
    xs=[0,2,3,0]
    ys=[0,0,3,2]
    R.set_xy(xs,ys)
    print(R.contains(1,0.2))
    print(R.contains(1,-0.5))
    
    lons=np.arange(100)
    lats=np.arange(111)
    Lons,Lats=np.meshgrid(lons,lats)
    grid=Grid(Lons,Lats)
    i,j=grid.find_ij(5,50)
