"""Download native windows, retain provenance, and report partial coverage honestly."""
from pathlib import Path
import hashlib,json,os
import numpy as np
from . import catalog,remote_dem as rd
from .dem import Raster,TerrainDEM,save_pack,download_context

def native_source(p,lat,lon,radius,cache,budget):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);asset=p.get('asset')
    if not asset:
        file=cache/('url_'+hashlib.sha256(p['page'].encode()).hexdigest()[:20]+'.json')
        if file.exists():asset=json.loads(file.read_text())['asset']
        else:asset=rd.resolve_nac(p['page']);file.write_text(json.dumps(dict(asset=asset)))
    source=rd.GeoTIFF(asset,budget) if p['kind']=='tiff' else rd.PDSRaster(asset,budget,p.get('label'))
    m=source.meta;c,r,w,h=rd.crop_window(m,lat,lon,radius)
    if min(w,h)<4:return
    existing=[]
    for path in list(cache.glob('native_*.npz'))+list(Path(__file__).with_name('data').glob('native_*.npz')):
        try:
            pack=Raster(path)
            if pack.meta.get('source_url')==asset:existing.append(pack.meta)
        except (ValueError,OSError,KeyError):continue
    for rr in range(r,r+h,4032):
        for cc in range(c,c+w,4032):
            ww,hh=min(4096,c+w-cc),min(4096,r+h-rr)
            if min(ww,hh)<4:continue
            if any(e.get('source_rows',[1,0])[0]<=rr and e['source_rows'][1]>=rr+hh and e.get('source_columns',[1,0])[0]<=cc and e['source_columns'][1]>=cc+ww for e in existing):
                yield 0.,'Cached native '+p['title'];continue
            key=hashlib.sha256(f'{asset}:{cc}:{rr}:{ww}:{hh}'.encode()).hexdigest()[:24];path=cache/f'native_{key}.npz'
            a=np.empty((hh,ww),np.float32)
            for row in range(0,hh,64):
                count=min(64,hh-row);a[row:row+count]=source.read_window(cc,rr+row,ww,count)
                yield row/max(1,hh),f"{p['title']}: {row+count}/{hh} native rows"
            if not np.isfinite(a).any():yield 1.,'No valid elevations: '+p['title'];continue
            pixel=1/m['ppd'] if m['projection']=='cylindrical' else m['pixel_m']
            meta=dict(m,title=p['title'],source_url=asset,source_page=p['page'],source_id=p['id'],west=m['west']+cc*pixel,north=m['north']-rr*pixel,width=ww,height=hh,scale=1.,source_rows=[rr,rr+hh],source_columns=[cc,cc+ww],blend_pixels=16.,resampling='None: original native cells',effective_resolution=p['effective_resolution'],requested_radius_m=radius)
            save_pack(path,a,meta);existing.append(meta);yield 1.,'Saved native '+p['title']

def download(latitude,longitude,radius_m,cache_dir,native_radius_m=2000,budget_mb=1024,report=None):
    lat,lon=float(latitude),float(longitude)%360;native_radius=min(radius_m,native_radius_m);cache=Path(cache_dir);cache.mkdir(parents=True,exist_ok=True)
    budget={'used':0,'limit':int(budget_mb*1024**2)};result=report if report is not None else {};result.clear()
    result.update(latitude=lat,longitude_east=lon,native_radius_m=native_radius,context_radius_m=radius_m,catalog_date=catalog.load()['snapshot_date'],completed=[],errors=[])
    context=TerrainDEM(lat,lon,cache);loaded=context.resolution_report(radius_m);threshold=60 if abs(lat)<60 else 500
    if max(loaded['perimeter_grids_m'],default=1e9)>threshold:
        try:yield from download_context(lat,lon,radius_m,cache,high=abs(lat)<60,budget=budget)
        except (OSError,ValueError) as e:result['errors'].append(dict(source='Context',error=str(e)))
    tasks=catalog.region(lat,lon,native_radius)+list(catalog.jaxa_tiles(lat,lon,native_radius))
    for p in tasks:
        if budget['used']>=budget['limit']:
            result['errors'].append(dict(source=p['id'],error='Download budget reached; remaining sources deferred'));break
        try:
            yield from native_source(p,lat,lon,native_radius,cache,budget);result['completed'].append(p['id'])
        except (OSError,ValueError,KeyError,StopIteration) as e:
            result['errors'].append(dict(source=p['id'],error=str(e)));yield 0.,'Using fallback for '+p['id']+': '+str(e)[:100]
    result.update(bytes_downloaded=budget['used'],budget_bytes=budget['limit'],complete=not result['errors'],loaded=TerrainDEM(lat,lon,cache).resolution_report(radius_m))
    temp=cache/'last_download_report.partial';temp.write_text(json.dumps(result,indent=2));os.replace(temp,cache/'last_download_report.json')
    yield 1.,'DEM download '+('complete' if result['complete'] else 'partial; inspect DEM report')
