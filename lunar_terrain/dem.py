"""Real lunar DEMs: bicubic sample centres, ENU geodesy, bounded PDS downloads."""
from pathlib import Path
import json,math,os,zipfile,hashlib,urllib.request
import numpy as np
from collections import OrderedDict
from . import remote_dem
_ARRAY_CACHE=OrderedDict()
RADIUS=1737400.
DATA=Path(__file__).with_name('data')
PDS='https://imbrium.mit.edu/DATA/'

def smooth(t):
    t=np.clip(t,0.,1.);return t*t*t*(t*(t*6-15)+10)

def interpolate(a,x,y,periodic=False):
    ix,iy=np.floor(x).astype(np.int64),np.floor(y).astype(np.int64)
    def weights(t):return (-.5*t+t*t-.5*t**3,1-2.5*t*t+1.5*t**3,.5*t+2*t*t-1.5*t**3,-.5*t*t+.5*t**3)
    wx,wy=weights(x-ix),weights(y-iy);z=np.zeros_like(x,dtype=float)
    for j in range(4):
        yy=np.clip(iy+j-1,0,a.shape[0]-1)
        for i in range(4):
            xx=(ix+i-1)%a.shape[1] if periodic else np.clip(ix+i-1,0,a.shape[1]-1)
            z+=a[yy,xx]*wx[i]*wy[j]
    return z

class Raster:
    def __init__(self,path):
        self.path=Path(path)
        with zipfile.ZipFile(path) as z:
            if any(i.file_size>320000000 for i in z.infolist()):raise ValueError('DEM pack exceeds the 320 MB member limit')
        with np.load(path,allow_pickle=False) as f:self.meta=json.loads(str(f['metadata']))
        with zipfile.ZipFile(path) as z:
            with z.open('elevation.npy') as f:
                version=np.lib.format.read_magic(f)
                shape,_,dtype=(np.lib.format.read_array_header_1_0(f) if version==(1,0) else np.lib.format.read_array_header_2_0(f))
        m=self.meta;self.shape=shape
        if len(shape)!=2 or min(shape)<4 or math.prod(shape)>80000000 or not np.issubdtype(dtype,np.number):raise ValueError('Invalid elevation grid')
        if m.get('schema')!=1 or abs(m.get('radius_m',0)-RADIUS)>.01:raise ValueError('Expected schema 1 and lunar radius 1737400 m')
        if m.get('projection') not in {'cylindrical','eqc','south_polar','north_polar'}:raise ValueError('Unsupported DEM projection')
        for key in ('west','north','scale','posting_m'):
            if not math.isfinite(float(m[key])):raise ValueError('Non-finite DEM metadata')
        spacing=m['ppd'] if m['projection']=='cylindrical' else m['pixel_m']
        if not math.isfinite(spacing) or spacing<=0 or m['posting_m']<=0:raise ValueError('Invalid DEM spacing')
        m['height'],m['width']=shape;self.posting=m['posting_m']
        self.blend=min(float(m.get('blend_pixels',max(12.,500/self.posting))),min(shape)/4)
        if self.blend<=0:raise ValueError('Invalid blend width')
        self._poles=None

    @property
    def a(self):
        st=self.path.stat();key=(str(self.path.resolve()),st.st_mtime_ns,st.st_size)
        if key not in _ARRAY_CACHE:
            with np.load(self.path,allow_pickle=False) as f:_ARRAY_CACHE[key]=f['elevation']
        _ARRAY_CACHE.move_to_end(key);a=_ARRAY_CACHE[key]
        while len(_ARRAY_CACHE)>1 and sum(v.nbytes for v in _ARRAY_CACHE.values())>384*1024**2:_ARRAY_CACHE.popitem(last=False)
        return a

    @property
    def poles(self):
        if self._poles is None:self._poles=(float(np.nanmean(self.a[0]))*self.meta['scale'],float(np.nanmean(self.a[-1]))*self.meta['scale'])
        return self._poles

    @property
    def validity(self):
        """Feather internal no-data edges into the next valid measured DEM.

        Reserve two cells for the bicubic stencil, then ramp confidence over
        sixteen valid cells. No extra dependency is needed inside Blender.
        """
        st=self.path.stat();key=('validity',str(self.path.resolve()),st.st_mtime_ns,st.st_size)
        if key not in _ARRAY_CACHE:
            a=self.a;valid=np.isfinite(a)&(np.abs(a*self.meta['scale'])<30000)
            if valid.all():confidence=np.empty(0,dtype=np.float32)
            else:
                interior=valid.copy();distance=np.zeros(a.shape,np.float32)
                for _ in range(18):
                    distance+=interior
                    padded=np.pad(interior,1,constant_values=True)
                    for dy in range(3):
                        for dx in range(3):interior&=padded[dy:dy+a.shape[0],dx:dx+a.shape[1]]
                confidence=smooth(np.clip((distance-2)/16,0,1)).astype(np.float32)
            _ARRAY_CACHE[key]=confidence
        _ARRAY_CACHE.move_to_end(key);result=_ARRAY_CACHE[key]
        while len(_ARRAY_CACHE)>1 and sum(v.nbytes for v in _ARRAY_CACHE.values())>384*1024**2:_ARRAY_CACHE.popitem(last=False)
        return result

    def sample(self,lat,lon):
        m=self.meta;lat,lon=np.broadcast_arrays(np.asarray(lat,dtype=float),np.asarray(lon,dtype=float))
        px,py=remote_dem.project(m,lat,lon);pixel=1/m['ppd'] if m['projection']=='cylindrical' else m['pixel_m']
        x=(px-m['west'])/pixel-.5;y=(m['north']-py)/pixel-.5
        periodic=bool(m.get('periodic',False))
        if periodic:
            top=np.full_like(y,1e9) if m['north']==90 else y+.5
            bottom=np.full_like(y,1e9) if abs(m['north']-self.shape[0]/m['ppd']+90)<1e-8 else self.shape[0]-.5-y
            edge=np.minimum(top,bottom)
        else:edge=np.minimum.reduce([x+.5,y+.5,self.shape[1]-.5-x,self.shape[0]-.5-y])
        w=smooth(edge/self.blend);keep=w>0;z=np.zeros_like(x,dtype=float)
        if np.any(keep):
            v=interpolate(self.a,x[keep],y[keep],periodic)*m['scale']
            confidence=self.validity
            if confidence.size:w[keep]*=np.clip(interpolate(confidence,x[keep],y[keep],periodic),0,1)
            if periodic:
                rho=(90-np.abs(lat[keep]))*m['ppd'];polar=rho<.5
                if np.any(polar):
                    t=smooth(rho[polar]/.5);pole=np.where(lat[keep][polar]>0,*self.poles)
                    v[polar]=v[polar]*t+pole*(1-t)
            good=np.isfinite(v)&(np.abs(v)<30000)
            z[keep]=np.where(good,v,0);w[keep]*=good
        return z,w

class TerrainDEM:
    def __init__(self,latitude,longitude,cache_dir=None,custom_pack=''):
        self.lat,self.lon=float(latitude),float(longitude)%360
        if not(-90<=self.lat<=90) or not math.isfinite(self.lon):raise ValueError('Invalid lunar latitude or longitude')
        paths=list(DATA.glob('*.npz'))
        if cache_dir and Path(cache_dir).is_dir():paths+=sorted(Path(cache_dir).glob('*.npz'))
        self.rasters=[];self.warnings=[]
        for path in paths:
            try:self.rasters.append(Raster(path))
            except (ValueError,OSError,KeyError,zipfile.BadZipFile) as e:self.warnings.append(f'Ignored {path.name}: {e}')
        if custom_pack:self.rasters.append(Raster(custom_pack))
        self.rasters.sort(key=lambda r:r.posting,reverse=True)
        if not any(r.meta.get('periodic') and r.shape[0]/r.meta.get('ppd',1)==180 for r in self.rasters):raise ValueError('Bundled global DEM is missing; install the complete ZIP')
        p,l=math.radians(self.lat),math.radians(self.lon)
        self.up=np.array([math.cos(p)*math.cos(l),math.cos(p)*math.sin(l),math.sin(p)])
        self.east=np.array([-math.sin(l),math.cos(l),0.]);self.north=np.cross(self.up,self.east)
        self.h0=float(self.elevation([self.lat],[self.lon])[0])

    def elevation(self,lat,lon):
        lat,lon=np.atleast_1d(lat),np.atleast_1d(lon);z=np.zeros_like(lat,dtype=float)
        for r in self.rasters:
            h,w=r.sample(lat,lon);z=z*(1-w)+h*w
        return z

    def geodetic(self,x,y,height=None):
        radius=RADIUS+(self.h0 if height is None else height)
        a,b=np.asarray(x)/radius,np.asarray(y)/radius;c=np.sqrt(np.maximum(0,1-a*a-b*b))
        v=a[...,None]*self.east+b[...,None]*self.north+c[...,None]*self.up
        return np.degrees(np.arcsin(v[...,2])),np.degrees(np.arctan2(v[...,1],v[...,0]))%360

    def height(self,x,y,curvature=True):
        x,y=np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float));shape=x.shape
        x,y=x.ravel(),y.ravel();out=np.empty_like(x)
        for start in range(0,len(x),100000):
            xx,yy=x[start:start+100000],y[start:start+100000]
            lat,lon=self.geodetic(xx,yy);h=self.elevation(lat,lon)
            lat,lon=self.geodetic(xx,yy,h);h=self.elevation(lat,lon)
            out[start:start+len(xx)]=np.sqrt((RADIUS+h)**2-xx*xx-yy*yy)-(RADIUS+self.h0) if curvature else h-self.h0
        return out.reshape(shape)

    def description(self,lat=None,lon=None):
        lat=self.lat if lat is None else lat;lon=self.lon if lon is None else lon;rows=[]
        for r in self.rasters:
            _,w=r.sample(np.array([lat]),np.array([lon]));weight=float(w[0])
            if weight>0:
                for row in rows:row['centre_weight']*=1-weight
                rows.append(dict(title=r.meta['title'],posting_m=r.posting,centre_weight=weight,source_url=r.meta.get('source_url',''),effective_resolution=r.meta.get('effective_resolution','Grid spacing; effective resolving power varies')))
        return [row for row in rows if row['centre_weight']>1e-8]

    def resolution_report(self,radius_m,focus_x=0.,focus_y=0.):
        from . import catalog
        a,b=self.geodetic([focus_x],[focus_y]);lat,lon=float(a[0]),float(b[0])
        t=np.linspace(0,2*np.pi,24,endpoint=False);a,b=self.geodetic(focus_x+radius_m*np.cos(t),focus_y+radius_m*np.sin(t))
        samples=[self.description(float(p),float(l)) for p,l in zip(a,b)]
        grids=sorted(set(max(rows,key=lambda x:x['centre_weight'])['posting_m'] for rows in samples if rows))
        return dict(latitude=self.lat,longitude_east=self.lon,available_at_origin=catalog.best(self.lat,self.lon),loaded_at_origin=self.description(),focus_xy_m=[focus_x,focus_y],focus_latitude=lat,focus_longitude=lon,loaded_at_focus=self.description(lat,lon),radius_m=radius_m,perimeter_grids_m=grids,perimeter_samples=24,meaning='Native grid spacing, not effective resolution or procedural mesh spacing. Perimeter uses 24 samples, not a coverage guarantee.')

def status_text(report,prefix='Built'):
    rows=report['loaded_at_origin'];best=min(rows,key=lambda x:x['posting_m'])
    text=f"{prefix} origin: {best['posting_m']:.3g} m grid"+(' (blended)' if len(rows)>1 else '')+' | '+best['title']
    if any(report.get('focus_xy_m',[0,0])):
        focus=min(report['loaded_at_focus'],key=lambda x:x['posting_m']);text+=f" | Detail focus: {focus['posting_m']:.3g} m grid"
    grids=', '.join(f'{p:.3g}' for p in report['perimeter_grids_m'])
    return text+f" | At {report['radius_m']/1000:g} km radius: {grids} m | 24 perimeter samples; grid ≠ effective resolution"

def save_pack(path,elevation,meta):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    meta=dict(meta,schema=1,radius_m=RADIUS,vertical_units='metres above 1737400 m sphere')
    tmp=path.with_suffix('.partial')
    try:
        with tmp.open('wb') as f:np.savez_compressed(f,elevation=elevation,metadata=np.array(json.dumps(meta)))
        Raster(tmp);os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

def _strip(url,start,end,total,budget=None):
    if budget is not None and budget['used']+end-start+1>budget['limit']:raise OSError('DEM download budget reached')
    req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}','User-Agent':'LunarTerrain/1.0','Accept-Encoding':'identity'})
    with urllib.request.urlopen(req,timeout=12) as response:
        if response.status!=206 or response.headers.get('Content-Range','')!=f'bytes {start}-{end}/{total}':raise OSError('Server ignored byte range; full-tile download stopped')
        data=response.read(end-start+2)
    if len(data)!=end-start+1:raise OSError('Incomplete DEM strip; retry download')
    if budget is not None:budget['used']+=len(data)
    return data

def download_context(latitude,longitude,radius_m,cache_dir,high=True,budget=None):
    lat,lon=float(latitude),float(longitude)%360;delta=math.degrees(radius_m/RADIUS)*1.12+.05
    north,south=min(90,lat+delta),max(-90,lat-delta)
    tasks=[dict(url=PDS+'LOLA_GDR/CYLINDRICAL/IMG/LDEM_64.IMG',width=23040,height=11520,ppd=64,dtype='<i2',scale=.5,north=90.,west=0.,r0=max(0,math.floor((90-north)*64)-16),r1=min(11520,math.ceil((90-south)*64)+16),c0=0,c1=23040,title='LOLA LDEM_64 v3.1',posting=473.8,periodic=True)]
    if high and south<60 and north>-60:
        lo_lat,hi_lat=max(-60,south),min(60,north);dx=min(180,delta/max(.02,math.cos(math.radians(max(abs(lo_lat),abs(hi_lat))))))
        for ts in (-60,-30,0,30):
            tn=ts+30
            if lo_lat>=tn or hi_lat<=ts:continue
            latname={-60:'60S_30S',-30:'30S_00S',0:'00N_30N',30:'30N_60N'}[ts]
            for west in range(0,360,45):
                for shift in (-360,0,360):
                    lo,hi=max(west,lon-dx+shift),min(west+45,lon+dx+shift)
                    if hi<=lo:continue
                    name=f'SLDEM2015_512_{latname}_{west:03d}_{west+45:03d}_FLOAT'
                    tasks.append(dict(url=PDS+f'SLDEM2015/TILES/FLOAT_IMG/{name}.IMG',width=23040,height=15360,ppd=512,dtype='<f4',scale=1000.,north=tn,west=west,r0=max(0,math.floor((tn-min(hi_lat,tn))*512)-16),r1=min(15360,math.ceil((tn-max(lo_lat,ts))*512)+16),c0=max(0,math.floor((lo-west)*512)-16),c1=min(23040,math.ceil((hi-west)*512)+16),title=name,posting=59.2253,periodic=False))
    total=sum(t['r1']-t['r0'] for t in tasks);done=0
    for t in tasks:
        key=hashlib.sha256(json.dumps(t,sort_keys=True).encode()).hexdigest()[:20];path=Path(cache_dir)/f'region_{key}.npz'
        if path.exists():
            try:
                Raster(path);done+=t['r1']-t['r0'];yield done/total,f"Cached {t['title']}";continue
            except (ValueError,OSError,KeyError,zipfile.BadZipFile):pass
        rowbytes=t['width']*np.dtype(t['dtype']).itemsize;strips=[];chunk=max(1,1500000//rowbytes)
        for start in range(t['r0'],t['r1'],chunk):
            end=min(start+chunk,t['r1']);data=_strip(t['url'],start*rowbytes,end*rowbytes-1,t['height']*rowbytes,budget)
            a=np.frombuffer(data,dtype=t['dtype']).reshape(end-start,t['width'])[:,t['c0']:t['c1']].astype(np.float32)*t['scale']
            if not np.isfinite(a).all() or np.max(np.abs(a))>30000:raise OSError('Invalid elevation values in DEM strip')
            strips.append(a);done+=end-start;yield done/total,f"Downloading {t['title']}: {end-t['r0']}/{t['r1']-t['r0']} rows"
        save_pack(path,np.concatenate(strips),dict(title=t['title'],projection='cylindrical',west=t['west']+t['c0']/t['ppd'],north=t['north']-t['r0']/t['ppd'],ppd=t['ppd'],scale=1.,posting_m=t['posting'],periodic=t['periodic'],source_url=t['url'],source_rows=[t['r0'],t['r1']],source_columns=[t['c0'],t['c1']]))
        yield done/total,f"Saved {t['title']}"


def download_region(latitude,longitude,radius_m,cache_dir,high=True,native_radius_m=2000,budget_mb=1024,report=None):
    from .dem_download import download
    yield from download(latitude,longitude,radius_m,cache_dir,native_radius_m,budget_mb,report)
