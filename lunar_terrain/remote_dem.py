"""Native lunar PDS/GeoTIFF windows. NumPy only; no GIS install in Blender."""
import math, re, struct, urllib.request, zlib
from collections import OrderedDict
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import numpy as np

RADIUS = 1737400.0
MPD = math.pi * RADIUS / 180

class RangeFile:
    def __init__(self, url, budget=None, allow_full=0):
        if urlparse(url).scheme != 'https': raise ValueError('DEM URL must use HTTPS')
        self.url=url; self.budget=budget if budget is not None else {'used':0,'limit':1024**3}
        self.allow_full=allow_full; self.full=None; self.total=None; self.cache=OrderedDict()

    def read(self, start, length):
        start,length=int(start),int(length)
        if start<0 or length<0 or length>16*1024**2: raise ValueError('Invalid or oversized byte window')
        if not length:return b''
        if self.full is not None:return self.full[start:start+length]
        for off,data in self.cache.items():
            if off<=start and start+length<=off+len(data):return data[start-off:start-off+length]
        off=start//65536*65536 if length<65536 else start
        size=max(65536,start+length-off) if length<65536 else length
        if self.total is not None:size=min(size,self.total-off)
        if self.budget['used']+size>self.budget['limit']:raise OSError('DEM download budget reached')
        req=urllib.request.Request(self.url,headers={'Range':f'bytes={off}-{off+size-1}','Accept-Encoding':'identity','User-Agent':'LunarTerrain/1.3'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req,timeout=20) as response:
                    self.url=response.geturl()
                    if response.status==200:
                        n=self.allow_full
                        if not n:raise ValueError('Server ignored byte range; full-file transfer refused')
                        if self.budget['used']+n>self.budget['limit']:raise ValueError('Full JAXA tile exceeds remaining download budget')
                        if response.headers.get('Content-Length') not in (None,str(n)):raise ValueError('Unexpected full-tile size')
                        data=response.read(n+1);self.budget['used']+=len(data)
                        if len(data)!=n:raise ValueError('Incomplete or oversized JAXA tile')
                        self.full=data;self.total=n
                        return data[start:start+length]
                    match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                    if response.status!=206 or not match:raise ValueError('Server did not return a verifiable byte range')
                    a,b,total=map(int,match.groups())
                    if a!=off or b!=min(off+size,total)-1 or (self.total is not None and total!=self.total):raise ValueError('DEM byte range changed')
                    self.total=total;data=response.read(b-a+2);self.budget['used']+=len(data)
                    if len(data)!=b-a+1:raise OSError('Incomplete DEM byte range')
                break
            except OSError:
                if attempt==2:raise
        self.cache[off]=data
        while sum(map(len,self.cache.values()))>32*1024**2:self.cache.popitem(last=False)
        return data[start-off:start-off+length]

def polar_scale(m):
    # ISIS/PDS CENTER_LATITUDE is the latitude of true scale. VIKRAMSITE1
    # uses -69.3 degrees, not the pole. Spherical k0=(1+sin(abs(lat_ts)))/2.
    latitude=float(m.get('standard_parallel',90.))
    if not math.isfinite(latitude) or not 0<abs(latitude)<=90:
        raise ValueError('Invalid polar true-scale latitude')
    return (1.+math.sin(math.radians(abs(latitude))))/2.

def project(m,lat,lon):
    lat,lon=np.asarray(lat,dtype=float),np.asarray(lon,dtype=float)
    kind=m['projection']
    if kind=='cylindrical':
        if m.get('periodic'):return m['west']+(lon-m['west'])%360,lat
        centre=m['west']+m['width']/m['ppd']/2
        return centre+(lon-centre+180)%360-180,lat
    if kind=='eqc':
        s=MPD*math.cos(math.radians(m.get('standard_parallel',0)));clon=m.get('central_longitude',0)
        centre=clon+(m['west']+m['width']*m['pixel_m']/2)/s
        longitude=centre+(lon-centre+180)%360-180
        return (longitude-clon)*s,(lat-m.get('origin_latitude',0))*MPD
    south=kind=='south_polar';phi=np.radians(lat);lam=np.radians(lon-m.get('central_longitude',0))
    rho=2*RADIUS*polar_scale(m)*np.tan(np.pi/4+phi/2 if south else np.pi/4-phi/2)
    return rho*np.sin(lam),rho*np.cos(lam)*(1 if south else -1)

def unproject(m,x,y):
    x,y=np.asarray(x),np.asarray(y);kind=m['projection']
    if kind=='cylindrical':return y,x%360
    if kind=='eqc':return y/MPD+m.get('origin_latitude',0),(x/(MPD*math.cos(math.radians(m.get('standard_parallel',0))))+m.get('central_longitude',0))%360
    south=kind=='south_polar';rho=np.hypot(x,y)
    return (np.degrees(2*np.arctan(rho/(2*RADIUS*polar_scale(m))))-90)*(1 if south else -1),(np.degrees(np.arctan2(x,y if south else -y))+m.get('central_longitude',0))%360

def boundary(lat,lon,radius,n=96):
    p,l=math.radians(lat),math.radians(lon);t=np.linspace(0,2*np.pi,n,endpoint=False);d=radius/RADIUS
    la=np.arcsin(np.clip(math.sin(p)*math.cos(d)+math.cos(p)*math.sin(d)*np.cos(t),-1,1))
    lo=l+np.arctan2(np.sin(t)*math.sin(d)*math.cos(p),math.cos(d)-math.sin(p)*np.sin(la))
    la=np.r_[math.degrees(p),np.degrees(la)];lo=np.r_[lon,np.degrees(lo)]
    if radius>=MPD*(90-abs(lat)):la=np.r_[la,90 if lat>=0 else -90];lo=np.r_[lo,lon]
    return la,lo%360

def crop_window(m,lat,lon,radius,pad=32):
    a,b=boundary(lat,lon,radius);x,y=project(m,a,b)
    pixel=1/m['ppd'] if m['projection']=='cylindrical' else m['pixel_m']
    c=(x-m['west'])/pixel;r=(m['north']-y)/pixel
    c0=max(0,int(np.floor(c.min()))-pad);r0=max(0,int(np.floor(r.min()))-pad)
    c1=min(m['width'],int(np.ceil(c.max()))+pad);r1=min(m['height'],int(np.ceil(r.max()))+pad)
    return c0,r0,max(0,c1-c0),max(0,r1-r0)

def _number(label,key,default=None):
    hit=re.search(r'^\s*'+re.escape(key)+r'\s*=\s*([+\-\d.eE]+)',label,re.M)
    return float(hit.group(1)) if hit else default

class PDSRaster:
    def __init__(self,url,budget=None,label_url=None):
        self.source_url=url;self.file=RangeFile(url,budget)
        if label_url:
            with urllib.request.urlopen(label_url,timeout=20) as f:label=f.read(131073).decode('ascii')
            if len(label)>131072:raise ValueError('Oversized PDS label')
        else:label=self.file.read(0,65536).decode('ascii',errors='replace').split('\nEND\n',1)[0]
        label=re.sub(r'/\*.*?\*/','',label,flags=re.S)
        w,h=int(_number(label,'LINE_SAMPLES')),int(_number(label,'LINES'))
        bits=int(_number(label,'SAMPLE_BITS'));typ=re.search(r'SAMPLE_TYPE\s*=\s*"?(\w+)',label).group(1)
        dt={('PC_REAL',32):'<f4',('IEEE_REAL',32):'>f4',('MSB_INTEGER',16):'>i2',('LSB_INTEGER',16):'<i2'}.get((typ,bits))
        if not dt:raise ValueError(f'Unsupported PDS sample type {typ}/{bits}')
        self.dtype=np.dtype(dt);self.offset=0 if label_url else int((_number(label,'^IMAGE',2)-1)*_number(label,'RECORD_BYTES'))
        if label_url and urlparse(url).hostname=='data.darts.isas.jaxa.jp' and (w,h,self.dtype.itemsize)==(4096,4096,2):self.file.allow_full=33554432
        scale=_number(label,'MAP_SCALE');line=re.search(r'^\s*MAP_SCALE\s*=([^\n]+)',label,re.M).group(1)
        if '<KM' in line.upper():scale*=1000
        kind=re.search(r'MAP_PROJECTION_TYPE\s*=\s*"?([A-Z_ ]+)',label).group(1).strip().strip('"')
        centre=_number(label,'CENTER_LATITUDE',0);clon=_number(label,'CENTER_LONGITUDE',0)
        proj=('south_polar' if centre<0 else 'north_polar') if 'POLAR' in kind else 'eqc'
        self.meta=dict(projection=proj,pixel_m=scale,posting_m=scale,width=w,height=h,west=-(_number(label,'SAMPLE_PROJECTION_OFFSET')+.5)*scale,north=(_number(label,'LINE_PROJECTION_OFFSET')+.5)*scale,standard_parallel=centre,origin_latitude=0.,central_longitude=clon,scale=1.)
        self.value_scale=_number(label,'SCALING_FACTOR',1);self.value_offset=_number(label,'OFFSET',0);self.nodata=_number(label,'DUMMY',-999999)

    def read_window(self,c,r,w,h):
        rowbytes=self.meta['width']*self.dtype.itemsize
        data=self.file.read(self.offset+r*rowbytes,h*rowbytes)
        a=np.frombuffer(data,dtype=self.dtype).reshape(h,self.meta['width'])[:,c:c+w].astype(np.float32)
        bad=(a==self.nodata)|~np.isfinite(a)|(np.abs(a)>=30000)
        a=a*self.value_scale+self.value_offset;a[bad]=np.nan
        return a

class GeoTIFF:
    """North-up lunar, single-band TIFF/BigTIFF; raw or Deflate, predictors 1/2/3."""
    def __init__(self,url,budget=None):
        self.source_url=url;self.file=RangeFile(url,budget);head=self.file.read(0,16)
        self.endian='<' if head[:2]==b'II' else '>';magic=struct.unpack(self.endian+'H',head[2:4])[0]
        if magic not in (42,43):raise ValueError('Not a TIFF elevation raster')
        big=magic==43;nf,es,of=('Q',20,8) if big else ('H',12,4)
        pos=struct.unpack(self.endian+('Q' if big else 'I'),head[8:16] if big else head[4:8])[0]
        n=struct.unpack(self.endian+nf,self.file.read(pos,8 if big else 2))[0]
        if n>1024:raise ValueError('Oversized TIFF directory')
        entries=self.file.read(pos+(8 if big else 2),n*es);self.tags={}
        formats={1:'B',2:'s',3:'H',4:'I',5:'II',6:'b',7:'B',8:'h',9:'i',11:'f',12:'d',16:'Q',17:'q',18:'Q'}
        for i in range(n):
            entry=entries[i*es:(i+1)*es];tag,typ=struct.unpack(self.endian+'HH',entry[:4]);count=struct.unpack(self.endian+('Q' if big else 'I'),entry[4:12] if big else entry[4:8])[0]
            if typ not in formats:continue
            fmt=formats[typ];size=(1 if typ==2 else struct.calcsize(self.endian+fmt))*count
            if size>16*1024**2:raise ValueError('TIFF tag exceeds memory limit')
            raw=entry[12:20] if big else entry[8:12]
            if size>of:raw=self.file.read(struct.unpack(self.endian+('Q' if big else 'I'),raw)[0],size)
            else:raw=raw[:size]
            self.tags[tag]=raw.decode('ascii',errors='replace').strip('\x00') if typ==2 else struct.unpack(self.endian+fmt*count,raw)
        t=self.tags;one=lambda key,default: t.get(key,(default,))[0]
        w,h=int(one(256,0)),int(one(257,0));bits=one(258,0);sf=one(339,1)
        if one(277,1)!=1 or bits not in (16,32,64):raise ValueError('Expected elevation, not an 8-bit browse image')
        self.dtype=np.dtype(self.endian+('f' if sf==3 else 'i' if sf==2 else 'u')+str(bits//8))
        self.compression=one(259,1);self.predictor=one(317,1)
        if self.compression not in (1,8,32946) or self.predictor not in (1,2,3):raise ValueError('Unsupported TIFF compression; use supplied DEM converter')
        if 34264 in t:raise ValueError('Rotated TIFF requires the supplied converter')
        scale=t[33550];tie=t[33922];keys=t[34735];geo={}
        for i in range(int(keys[3])):
            key,loc,count,off=keys[4+i*4:8+i*4]
            geo[key]=off if loc==0 else t[loc][off] if loc!=34737 else t[loc][off:off+count]
        radius=float(geo.get(2057,RADIUS))
        if abs(radius-RADIUS)>.01:raise ValueError('TIFF lunar reference radius differs from 1737400 m')
        if 2057 not in geo and 'MOON' not in str(t.get(34737,'')).upper():raise ValueError('TIFF is not identified as lunar')
        ct=geo.get(3075);lat=float(geo.get(3081,geo.get(3085,0)));clon=float(geo.get(3080,geo.get(3084,geo.get(3095,0))))
        if any(abs(float(geo.get(k,0)))>1e-8 for k in (3082,3083,3086,3087)):raise ValueError('TIFF false offsets require converter')
        if abs(float(geo.get(3092,geo.get(3093,1)))-1)>1e-8:raise ValueError('TIFF non-unit polar scale requires converter')
        kind='eqc' if ct==17 else ('south_polar' if lat<0 else 'north_polar') if ct in (14,15) else 'cylindrical' if geo.get(1024)==2 else None
        if kind is None:raise ValueError('Unsupported TIFF map projection')
        west=tie[3]-tie[0]*scale[0];north=tie[4]+tie[1]*scale[1]
        if geo.get(1025)==2:west-=scale[0]/2;north+=scale[1]/2
        if abs(scale[0]-scale[1])>1e-8:raise ValueError('Non-square TIFF cells require converter')
        self.meta=dict(projection=kind,west=west,north=north,pixel_m=scale[0],posting_m=scale[0],width=w,height=h,scale=1.,standard_parallel=float(geo.get(3078,lat)),origin_latitude=lat if ct==17 else 0.,central_longitude=clon)
        if kind=='cylindrical':self.meta.update(ppd=1/scale[0],posting_m=scale[0]*MPD)
        self.tw=int(one(322,w));self.th=int(one(323,one(278,h)));self.offsets=t.get(324,t.get(273));self.counts=t.get(325,t.get(279));self.tiled=324 in t
        self.nodata=float(str(t.get(42113,'nan')).strip());self.blocks=OrderedDict()

    def block(self,index):
        if index in self.blocks:return self.blocks[index]
        raw=self.file.read(self.offsets[index],self.counts[index]);raw=zlib.decompress(raw) if self.compression!=1 else raw
        width=self.tw;rows=len(raw)//(width*self.dtype.itemsize)
        if self.predictor==3:
            b=np.frombuffer(raw,dtype=np.uint8).reshape(rows,-1);b=np.cumsum(b,axis=1,dtype=np.uint64).astype(np.uint8)
            b=b.reshape(rows,self.dtype.itemsize,width).transpose(0,2,1)
            if self.endian=='<':b=b[:,:,::-1]
            a=np.ascontiguousarray(b).view(self.dtype).reshape(rows,width)
        else:
            a=np.frombuffer(raw,dtype=self.dtype).reshape(rows,width)
            if self.predictor==2:a=np.cumsum(a,axis=1).astype(self.dtype)
        self.blocks[index]=a
        while sum(v.nbytes for v in self.blocks.values())>32*1024**2:self.blocks.popitem(last=False)
        return a

    def read_window(self,c,r,w,h):
        a=np.full((h,w),np.nan,np.float32);nx=math.ceil(self.meta['width']/self.tw)
        for ty in range(r//self.th,(r+h-1)//self.th+1):
            for tx in range(c//self.tw,(c+w-1)//self.tw+1):
                b=self.block(ty*nx+tx);x0=max(c,tx*self.tw);y0=max(r,ty*self.th);x1=min(c+w,(tx+1)*self.tw);y1=min(r+h,ty*self.th+b.shape[0])
                a[y0-r:y1-r,x0-c:x1-c]=b[y0-ty*self.th:y1-ty*self.th,x0-tx*self.tw:x1-tx*self.tw]
        a[(a==self.nodata)|~np.isfinite(a)|(np.abs(a)>=30000)]=np.nan
        return a

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.href=None;self.label=''
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.href=dict(attrs).get('href');self.label=''
    def handle_data(self,data):
        if self.href:self.label+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.href:self.links.append((self.href,self.label));self.href=None

def page_links(url):
    with urllib.request.urlopen(url,timeout=20) as f:content=f.read(4000000).decode('utf-8',errors='replace')
    p=Links();p.feed(content);return [(urljoin(url,h),label) for h,label in p.links]

def resolve_nac(page):
    links=page_links(page)
    direct=[u for u,label in links if u.upper().endswith('.IMG') and 'DTM' in u.upper()]
    if direct:return direct[0]
    detail=next((u for u,label in links if 'Digital Terrain Model (PDS IMG)' in label),None)
    if detail is None:raise ValueError('No native PDS elevation link on the catalog page')
    asset=next((u for u,label in page_links(detail) if u.upper().endswith('.IMG')),None)
    if asset is None:raise ValueError('Native PDS elevation asset is unavailable')
    return asset
