"""One connected circular LOD mesh; synthetic sub-DEM geology is explicit."""
from pathlib import Path
import csv,math
import numpy as np
from .dem import interpolate,smooth

def gradient_noise(x,y,wavelength,seed):
    u=(x*.917+y*.399)/wavelength+seed*.123;v=(-x*.399+y*.917)/wavelength-seed*.317
    ix,iy=np.floor(u).astype(np.int64),np.floor(v).astype(np.int64);fx,fy=u-ix,v-iy
    wx,wy=smooth(fx),smooth(fy);values=[]
    for dy in (0,1):
        row=[]
        for dx in (0,1):
            with np.errstate(over='ignore'):
                h=(ix+dx).astype(np.uint64)*np.uint64(374761393)+(iy+dy).astype(np.uint64)*np.uint64(668265263)+np.uint64(seed*104729)
                h=(h^(h>>np.uint64(13)))*np.uint64(1274126177);h^=h>>np.uint64(16)
            a=(h&np.uint64(65535)).astype(float)*(2*np.pi/65536)
            row.append(np.cos(a)*(fx-dx)+np.sin(a)*(fy-dy))
        values.append(row[0]*(1-wx)+row[1]*wx)
    return values[0]*(1-wy)+values[1]*wy

class CraterLayer:
    def __init__(self,radius,spacing,craters):
        self.radius,self.spacing=radius,spacing;self.half=math.ceil((radius+14)/spacing)*spacing
        size=int(round(2*self.half/spacing))+1
        if size*size>30000000:raise ValueError('Crater grid exceeds memory budget; reduce detail radius or increase spacing')
        self.a=np.zeros((size,size),np.float32);self.craters=craters

    def build(self):
        for index,(cx,cy,d,dd,angle,e,p1,p2) in enumerate(self.craters):
            r=d/2;support=r*1.8;step=self.spacing;half=self.half
            x0=max(0,int((cx-support+half)/step));x1=min(self.a.shape[1],int((cx+support+half)/step)+2)
            y0=max(0,int((cy-support+half)/step));y1=min(self.a.shape[0],int((cy+support+half)/step)+2)
            x=(np.arange(x0,x1)*step-half-cx)[None,:];y=(np.arange(y0,y1)*step-half-cy)[:,None]
            u,v=x*np.cos(angle)+y*np.sin(angle),-x*np.sin(angle)+y*np.cos(angle);theta=np.arctan2(v,u)
            q=np.sqrt((u/(1+e))**2+(v*(1+e))**2)/r
            q/=1+.075*np.sin(3*theta+p1)+.045*np.sin(5*theta+p2)
            bowl=-dd*d*np.maximum(0,1-q*q)**2;rim=.12*dd*d*np.exp(-((q-1)/.22)**2)
            self.a[y0:y1,x0:x1]+=(bowl+rim)*(1-smooth((q-1.25)/.4))
            if index%400==0:yield index/max(1,len(self.craters))

    def height(self,x,y):
        rr=np.hypot(x,y);keep=rr<self.radius;z=np.zeros_like(x,dtype=float)
        if np.any(keep):z[keep]=interpolate(self.a,(x[keep]+self.half)/self.spacing,(y[keep]+self.half)/self.spacing)*(1-smooth((rr[keep]-.78*self.radius)/(.22*self.radius)))
        return z

class Surface:
    def __init__(self,dem,settings):self.dem,self.cfg=dem,settings;self.layers=[];self.crater_count=0;self.crater_rows=[];self.micro_crater_count=0
    def prepare(self):
        cfg=self.cfg;rng=np.random.default_rng(cfg.seed)
        with (Path(__file__).with_name('data')/'CE6_reference_craters.csv').open() as f:records=list(csv.DictReader(f))
        diam=np.array([float(r['diameter_m']) for r in records]);dd=np.array([float(r['depth_diameter_ratio'] or 'nan') for r in records])
        valid=dd[np.isfinite(dd)&(dd>0)&(dd<.3)]
        for lo,hi,radius,spacing in [(.52,2.,cfg.detail_radius*1.4,max(.085,cfg.mesh_spacing*.6)),(2.,10.,min(cfg.outer_radius*.8,cfg.detail_radius*5.5),max(.3,cfg.mesh_spacing*2))]:
            pool=diam[(diam>=lo)&(diam<hi)];density=len(pool)/1600*cfg.crater_density
            count=int(rng.poisson(density*np.pi*radius**2))
            if count>30000:raise ValueError('More than 30,000 craters in one layer; reduce radius or abundance')
            d=rng.choice(pool,count);depths=rng.choice(valid,count)*cfg.crater_depth;r=np.sqrt(rng.random(count))*radius;a=rng.random(count)*2*np.pi
            cr=np.column_stack((r*np.cos(a),r*np.sin(a),d,depths,rng.uniform(0,2*np.pi,count),rng.uniform(.02,.18,count),rng.uniform(0,2*np.pi,count),rng.uniform(0,2*np.pi,count)))
            self.crater_rows.extend(cr.tolist());layer=CraterLayer(radius,spacing,cr)
            for prog in layer.build():yield f'Sculpting worn {lo:g}–{hi:g} m craters ({prog:.0%})'
            self.layers.append(layer);self.crater_count+=count
        radius=min(24.,cfg.detail_radius*.85);count=int(rng.poisson(cfg.micro_craters*np.pi*radius**2))
        r=np.sqrt(rng.random(count))*radius;a=rng.uniform(0,2*np.pi,count)
        d=(.20**-1.7+rng.random(count)*(.52**-1.7-.20**-1.7))**(-1/1.7)
        cr=np.column_stack((r*np.cos(a),r*np.sin(a),d,rng.uniform(.08,.20,count)*cfg.crater_depth,rng.uniform(0,2*np.pi,count),rng.uniform(.05,.22,count),rng.uniform(0,2*np.pi,count),rng.uniform(0,2*np.pi,count)))
        layer=CraterLayer(radius,max(.04,cfg.mesh_spacing*.5),cr)
        for _ in layer.build():yield 'Adding artist-authored sub-catalogue craterlets'
        self.layers.append(layer);self.micro_crater_count=count
        yield f'{self.crater_count:,} analogue craters; {count:,} artistic small craterlets'

    def height(self,x,y):
        x,y=np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float));shape=x.shape;x,y=x.ravel(),y.ravel()
        z=self.dem.height(x,y,self.cfg.curvature);x,y=x-self.cfg.focus_x,y-self.cfg.focus_y;r=np.hypot(x,y)
        for wavelength,amp,extent,offset in [(12,.07,7,11),(2.8,.025,4,17),(.65,.022,2,23),(.32,.008,1,29)]:
            keep=r<self.cfg.detail_radius*extent
            if np.any(keep):z[keep]+=self.cfg.roughness*amp*gradient_noise(x[keep],y[keep],wavelength,self.cfg.seed+offset)*(1-smooth((r[keep]/self.cfg.detail_radius/extent-.60)/.40))
        for layer in self.layers:z+=layer.height(x,y)
        return z.reshape(shape)

def radial_mesh(surface,cfg):
    rings=[];r=0.;count=1
    while r<cfg.outer_radius:
        step=cfg.mesh_spacing*max(1.,(r/cfg.detail_radius)**1.30);r=min(cfg.outer_radius,r+step)
        n=max(64,int(math.ceil(2*np.pi*r/step/4))*4);rings.append((r,n,count));count+=n
        if count>2800000:raise ValueError('Terrain exceeds 2.8 million vertices; increase near spacing or reduce detail radius')
    vertices=np.empty((count,3),np.float32);vertices[0]=(cfg.focus_x,cfg.focus_y,0);lod=np.zeros(count,np.int32)
    for r,n,start in rings:
        a=np.arange(n)*2*np.pi/n;vertices[start:start+n,0]=r*np.cos(a)+cfg.focus_x;vertices[start:start+n,1]=r*np.sin(a)+cfg.focus_y
        lod[start:start+n]=max(0,int(math.log(max(1.,r/cfg.detail_radius),4))+1) if r>cfg.detail_radius else 0
    for start in range(0,count,100000):
        v=vertices[start:start+100000];v[:,2]=surface.height(v[:,0],v[:,1]);yield f'Sampling elevation: {start+len(v):,}/{count:,}'
    faces=np.empty((2*count-rings[-1][1]-2,3),np.int32);cursor=0;_,n,start=rings[0]
    for j in range(n):faces[cursor]=(0,start+j,start+(j+1)%n);cursor+=1
    for ring_index,((_,m,s0),(_,n,s1)) in enumerate(zip(rings[:-1],rings[1:])):
        i=j=0
        while i<m or j<n:
            inner,outer=s0+i%m,s1+j%n;ai=(i+1)*n if i<m else 10**20;aj=(j+1)*m if j<n else 10**20
            if ai==aj:
                faces[cursor]=(inner,outer,s1+(j+1)%n);faces[cursor+1]=(inner,s1+(j+1)%n,s0+(i+1)%m);cursor+=2;i+=1;j+=1
            elif ai<aj:faces[cursor]=(inner,outer,s0+(i+1)%m);cursor+=1;i+=1
            else:faces[cursor]=(inner,outer,s1+(j+1)%n);cursor+=1;j+=1
        if ring_index%120==0:yield f'Joining continuous rings: {ring_index+1}/{len(rings)}'
    assert cursor==len(faces)
    return vertices,faces,lod

def rock_samples(surface,cfg):
    rng=np.random.default_rng(cfg.seed+401);k=cfg.rock_coverage;beta=.5648+.01258/max(k,1e-9);pts=[];stats=[]
    for lo,hi,radius in [(cfg.min_rock,.20,cfg.detail_radius*1.4),(.20,1.5,min(cfg.outer_radius*.8,cfg.detail_radius*6))]:
        if k<=0 or hi<=lo:continue
        d=np.geomspace(lo,hi,4096);number=4*k*beta*np.exp(-beta*d)/(np.pi*d*d)
        cdf=np.r_[0,np.cumsum((number[1:]+number[:-1])*.5*np.diff(d))];density=float(cdf[-1]);cdf/=max(density,1e-12)
        count=int(rng.poisson(density*np.pi*radius**2))
        if count+sum(len(p) for p in pts)>cfg.max_rocks:raise ValueError('Rock instance cap exceeded; reduce radius/coverage or increase minimum size/cap')
        diameter=np.interp(rng.random(count),cdf,d);r=np.sqrt(rng.random(count))*radius;a=rng.random(count)*2*np.pi
        pts.append(np.column_stack((r*np.cos(a),r*np.sin(a),diameter)))
        stats.append(dict(min_diameter_m=lo,max_diameter_m=hi,radius_m=radius,number_density_per_m2=density,instances=count))
    samples=np.concatenate(pts) if pts else np.empty((0,3));radius=min(20.,cfg.detail_radius*.8)
    count=int(rng.poisson(cfg.micro_density*np.pi*radius**2))
    if len(samples)+count>cfg.max_rocks:raise ValueError('Fine fragments exceed rock instance cap')
    if count:
        lo,hi=.005,min(.025,cfg.min_rock);exponent=-1.4
        d=(lo**exponent+rng.random(count)*(hi**exponent-lo**exponent))**(1/exponent)
        r=np.sqrt(rng.random(count))*radius;a=rng.random(count)*2*np.pi
        samples=np.concatenate((samples,np.column_stack((r*np.cos(a),r*np.sin(a),d))))
        stats.append(dict(min_diameter_m=lo,max_diameter_m=hi,radius_m=radius,number_density_per_m2=cfg.micro_density,instances=count,basis='Artist-authored, not a measured site population'))
    xyz=np.zeros((len(samples),3),np.float32);xyz[:,:2]=samples[:,:2]+[cfg.focus_x,cfg.focus_y]
    xyz[:,2]=surface.height(xyz[:,0],xyz[:,1])-.07*samples[:,2]
    rotation=np.zeros_like(xyz);rotation[:,2]=rng.uniform(0,2*np.pi,len(samples));idx=rng.integers(0,12,len(samples),dtype=np.int32)
    idx+=12*((samples[:,2]<.15)|(np.hypot(samples[:,0],samples[:,1])>cfg.detail_radius*3))
    return xyz,samples[:,2].astype(np.float32),rotation,idx,stats
