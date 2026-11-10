"""Refresh public footprints. Development only: pip install pyshp shapely numpy."""
from pathlib import Path
import sys,json,urllib.request,zipfile,io,importlib.util,datetime
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import shapefile
from shapely.geometry import shape,mapping,Polygon,box
from shapely.affinity import translate

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('remote_dem',ROOT/'lunar_terrain/remote_dem.py');rd=importlib.util.module_from_spec(spec);spec.loader.exec_module(rd)
URL='https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/EXTRAS/SHAPEFILE/NAC_DTMS/NAC_DTMS_180.ZIP'
BASE='https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/DATA/SDP/NAC_DTM/'
KNOWN={k:BASE+k+'/'+v+'.IMG' for k,v in [('APOLLO17_2M','NAC_DTM_APOLLO17_2M_E201N0307'),('CHANGE6','NAC_DTM_CHANGE6_E421S2060'),('ESALL_CR1','NAC_DTM_ESALL_CR1_P895S2222')]}

def nasa(url):
    raster=rd.GeoTIFF(url);m=raster.meta;west,north=m['west'],m['north'];east=west+m['width']*m['pixel_m'];south=north-m['height']*m['pixel_m']
    t=np.linspace(0,1,96);x=np.r_[west+(east-west)*t,np.full(96,east),east+(west-east)*t,np.full(96,west)];y=np.r_[np.full(96,north),north+(south-north)*t,np.full(96,south),south+(north-south)*t]
    lat,lon=rd.unproject(m,x,y);lon=np.degrees(np.unwrap(np.radians(lon)))
    coords=list(zip(lon,lat))
    if west<=0<=east and south<=0<=north:coords.extend([(lon[-1],-90),(lon[0],-90)])
    p=Polygon(coords).buffer(0);pieces=[]
    for shift in range(-3,4):
        part=translate(p,xoff=shift*360).intersection(box(-180,-90,180,90))
        if part.is_empty:continue
        pieces.extend(list(part.geoms) if part.geom_type=='MultiPolygon' else [part])
    polys=[mapping(g)['coordinates'] for g in pieces if g.geom_type=='Polygon']
    ident=Path(url).stem;return dict(type='Feature',geometry=dict(type='MultiPolygon',coordinates=polys),properties=dict(id=ident,title='Adjusted LOLA '+ident,kind='tiff',posting_m=m['posting_m'],page='https://pgda.gsfc.nasa.gov/products/78',asset=url,raster=m,effective_resolution='5 m grid; many cells interpolate between laser tracks. Effective resolution varies; see NASA uncertainty and EFFRES products.'))

def main():
    directory=ROOT/'tools/catalog_source';directory.mkdir(exist_ok=True)
    path=directory/'NAC_DTMS_180.ZIP'
    if not path.exists():path.write_bytes(urllib.request.urlopen(URL,timeout=40).read())
    with zipfile.ZipFile(path) as z:z.extractall(directory)
    shp=next(directory.rglob('*.SHP'));features=[]
    reader=shapefile.Reader(str(shp),encoding='latin1')
    for sr in reader.iterShapeRecords():
        r={k.lower():v for k,v in sr.record.as_dict().items()};ident=str(r['dtm_name']);geom=shape(sr.shape.__geo_interface__).simplify(.00001,preserve_topology=True)
        p=dict(id=ident,title='LROC NAC '+ident,kind='nac',posting_m=float(r['resolution']),page='https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_'+ident,effective_resolution='Stereo DEM grid; effective resolution and vertical precision vary. Consult product readme and stereo error metrics.',completion=str(r.get('completion','')))
        if ident in KNOWN:p['asset']=KNOWN[ident]
        features.append(dict(type='Feature',properties=p,geometry=mapping(geom)))
    urls=sorted(set(u for u,label in rd.page_links('https://pgda.gsfc.nasa.gov/products/78') if u.lower().endswith('5mpp_surf.tif')))
    with ThreadPoolExecutor(max_workers=5) as pool:
        for f in pool.map(nasa,urls):features.append(f);print('NASA',f['properties']['id'],flush=True)
    baseline=dict(id='SLDEM2013',title='JAXA SLDEM2013',kind='global',posting_m=rd.MPD/4096,ppd=4096,page='https://darts.isas.jaxa.jp/en/datasets/darts:sln-l-tc-5-sldem2013-v1.0/',effective_resolution='7.403 m nominal north-south grid; primary TC input about 10 m, with MI/LOLA fill, smoothing and resampling. Effective detail is coarser and variable.')
    result=dict(type='FeatureCollection',schema=1,snapshot_date=str(datetime.date.today()),nac_release_through='2026-06-15',baseline=baseline,features=features,scope='Finest published grid in supported public catalogs, not an exhaustive inventory of every research or surface-photogrammetry DEM.',sources=[URL,'https://pgda.gsfc.nasa.gov/products/78',baseline['page']])
    # Round coordinates to sub-metre precision while keeping metadata exact.
    def round_coords(a):return [round_coords(v) for v in a] if isinstance(a,(list,tuple)) else round(float(a),7)
    for f in features:f['geometry']['coordinates']=round_coords(f['geometry']['coordinates'])
    target=ROOT/'lunar_terrain/data/dem_catalog.geojson';target.write_text(json.dumps(result,separators=(',',':')))
    print('CATALOG',len(features),target.stat().st_size,flush=True)

if __name__=='__main__':main()
