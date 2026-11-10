"""Finest native grid in a dated, public DEM catalog; footprints are not valid-pixel guarantees."""
from pathlib import Path
from functools import lru_cache
import json,math
from .remote_dem import project,MPD

@lru_cache(maxsize=1)
def load():
    data=json.loads(Path(__file__).with_name('data').joinpath('dem_catalog.geojson').read_text())
    for f in data['features']:
        g=f['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
        f['_polys']=polys;f['_bounds']=[(min(x for x,y in p[0]),min(y for x,y in p[0]),max(x for x,y in p[0]),max(y for x,y in p[0])) for p in polys]
    return data

def ring_contains(ring,x,y):
    inside=False
    for (a,b),(c,d) in zip(ring,ring[1:]+ring[:1]):
        if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:inside=not inside
    return inside

def contains(f,lat,lon):
    p=f['properties'];m=p.get('raster')
    if m:
        x,y=project(m,lat,lon)
        return m['west']<=x<=m['west']+m['width']*m['pixel_m'] and m['north']-m['height']*m['pixel_m']<=y<=m['north']
    lon=(lon+180)%360-180
    for poly,(a,b,c,d) in zip(f['_polys'],f['_bounds']):
        if a<=lon<=c and b<=lat<=d and ring_contains(poly[0],lon,lat) and not any(ring_contains(h,lon,lat) for h in poly[1:]):return True
    return False

def order(p):return (p['posting_m'],0 if p.get('asset') else 1,p['id'])

@lru_cache(maxsize=128)
def at(lat,lon):
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90:raise ValueError('Invalid coordinates')
    data=load();return sorted([f['properties'] for f in data['features'] if contains(f,lat,lon)]+[data['baseline']],key=order)

def best(lat,lon):return at(round(float(lat),7),round(float(lon)%360,7))[0]

def region(lat,lon,radius):
    delta=radius/MPD*1.03+.001;bottom=max(-90,lat-delta);top=min(90,lat+delta)
    dx=180 if bottom<=-90 or top>=90 else min(180,delta/max(.0001,math.cos(math.radians(max(abs(bottom),abs(top))))))
    centre=(lon+180)%360-180;out=[]
    for f in load()['features']:
        if any(d>=bottom and b<=top and any(c>=centre-dx+s and a<=centre+dx+s for s in (-360,0,360)) for a,b,c,d in f['_bounds']):out.append(f['properties'])
    return sorted(out,key=order)

def jaxa_tiles(lat,lon,radius):
    delta=radius/MPD*1.03+.001;bottom=max(-90,lat-delta);top=min(90,lat+delta)
    dx=180 if bottom<=-90 or top>=90 else min(180,delta/max(.0001,math.cos(math.radians(max(abs(bottom),abs(top))))))
    def ns(v):return ('N' if v>=0 else 'S')+f'{abs(v):02d}'
    for south in range(max(-90,math.floor(bottom)),min(90,math.ceil(top))):
        for west in sorted(set(v%360 for v in range(math.floor(lon-dx),math.ceil(lon+dx)))):
            name=f'DTM_MAP_01_{ns(south+1)}E{west:03d}{ns(south)}E{west+1:03d}SC'
            url=f'https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-tc-5-sldem2013-v1.0/lon{west:03d}/data/{name}.img'
            yield dict(load()['baseline'],id=name,title='JAXA SLDEM2013 '+name,kind='pds',asset=url,label=url[:-4]+'.lbl')
