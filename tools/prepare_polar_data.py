"""Prepare bounded native polar crops and 80 m context; NumPy only, no GDAL."""
from pathlib import Path
import hashlib,json,sys,types,urllib.request
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
module=types.ModuleType('lunar_terrain');module.__path__=[str(ROOT/'lunar_terrain')];sys.modules['lunar_terrain']=module
from lunar_terrain import catalog,dem,dem_download,remote_dem as rd
SITES=[('VIPER',-85.42088,31.6218,'Site20'),('NOBILE2',-83.954,58.82206,'DM2'),('MALAPERT',-85.9948,359.76422,'Site23')]

def prepare():
    cache=ROOT/'build/polar_sources';cache.mkdir(parents=True,exist_ok=True)
    destination=ROOT/'lunar_terrain/data';results=[]
    for key,lat,lon,region in SITES:
        url=f'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/{region}/{region}_final_adj_5mpp_surf.tif'
        local=cache/(region+'.tif')
        if not local.exists():
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url,timeout=45) as response,local.with_suffix('.partial').open('wb') as stream:
                        size=0
                        while chunk:=response.read(1024**2):
                            size+=len(chunk)
                            if size>256*1024**2:raise ValueError('Regional TIFF exceeds 256 MiB limit')
                            stream.write(chunk)
                    local.with_suffix('.partial').replace(local);break
                except OSError:
                    if attempt==2:raise
        class LocalRange:
            def __init__(self,*args,**kwargs):pass
            def read(self,start,length):
                with local.open('rb') as stream:stream.seek(start);data=stream.read(length)
                if len(data)!=length:raise OSError('Truncated regional TIFF')
                return data
        with patch.object(rd,'RangeFile',LocalRange):source=rd.GeoTIFF(url)
        m=source.meta;assert m['posting_m']==5 and m['projection']=='south_polar'
        a=source.read_window(0,0,m['width'],m['height']);c,r,w,h=rd.crop_window(m,lat,lon,2200)
        with local.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        metadata=dict(m,title=f'Adjusted LOLA {region} 5 m',source_url=url,source_page='https://pgda.gsfc.nasa.gov/products/78',source_id=region,source_sha256=digest,resampling='None: original native cells',blend_pixels=16.,effective_resolution='5 m interpolated LOLA grid; resolving power varies with laser-track spacing')
        native=dict(metadata,west=m['west']+c*5,north=m['north']-r*5,width=w,height=h,source_rows=[r,r+h],source_columns=[c,c+w])
        keyhash=hashlib.sha256(f'{url}:{c}:{r}:{w}:{h}'.encode()).hexdigest()[:24]
        dem.save_pack(destination/f'native_{keyhash}.npz',a[r:r+h,c:c+w],native)
        nh,nw=a.shape[0]//16,a.shape[1]//16;blocks=a[:nh*16,:nw*16].reshape(nh,16,nw,16);counts=np.isfinite(blocks).sum(axis=(1,3))
        coarse=np.divide(np.nansum(blocks,axis=(1,3)),counts,out=np.full((nh,nw),np.nan),where=counts>0).astype(np.float32)
        context=dict(metadata,title=f'Adjusted LOLA {region} regional context (80 m)',width=nw,height=nh,pixel_m=80.,posting_m=80.,resampling='16 by 16 native 5 m cells averaged to 80 m')
        dem.save_pack(destination/f'polar_{key}_context80.npz',coarse,context);del a,blocks,coarse
        budget={'used':0,'limit':512*1024**2}
        if max(dem.TerrainDEM(lat,lon).resolution_report(20000)['perimeter_grids_m'],default=9999)>500:
            for progress,message in dem.download_context(lat,lon,20000,destination,high=False,budget=budget):
                if progress>=.99:print(message,flush=True)
        best=catalog.best(lat,lon)
        if best['posting_m']<5:
            for progress,message in dem_download.native_source(best,lat,lon,2200,destination,budget):
                if progress>=.99:print(message,flush=True)
        report=dem.TerrainDEM(lat,lon).resolution_report(20000);actual=min(x['posting_m'] for x in report['loaded_at_origin']);assert actual<=5
        results.append(dict(preset=key,actual_origin_grid_m=actual,resolution=report));print(key,'loaded',actual,'m',flush=True)
    (cache/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':prepare()
