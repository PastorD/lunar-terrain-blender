"""Independent GDAL checks of original PDS and BigTIFF bytes, plus native seam tests."""
from pathlib import Path
import sys,types,json,tempfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import numpy as np
import rasterio
from rasterio.windows import Window
ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('lunar_terrain');pkg.__path__=[str(ROOT/'lunar_terrain')];sys.modules['lunar_terrain']=pkg
from lunar_terrain import dem,catalog,remote_dem as rd,dem_download

def independent(site):
    lat,lon,want=site;p=catalog.best(lat,lon);assert p['posting_m']==want
    source=rd.PDSRaster(p['asset']);m=source.meta;x,y=rd.project(m,lat,lon);c=int((x-m['west'])/m['pixel_m']);r=int((m['north']-y)/m['pixel_m']);a=source.read_window(c,r,8,8)
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/'original.IMG'
        with path.open('wb') as f:
            f.truncate(source.file.total)
            for off,raw in source.file.cache.items():f.seek(off);f.write(raw)
        with rasterio.open(path) as ds:
            ref=ds.read(1,window=Window(c,r,8,8)).astype(np.float32);assert np.array_equal(a,ref,equal_nan=True)
            px,py=ds.xy(r,c);expected=(m['west']+(c+.5)*m['pixel_m'],m['north']-(r+.5)*m['pixel_m']);error=float(np.max(np.abs(np.array([px,py])-expected)));assert error<1e-5
    print('PDS/GDAL PASS',p['id'],flush=True);return dict(site=p['id'],grid_m=want,exact_samples=64,pixel_centre_error_m=error)

def run():
    with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(independent,[(20.1908,30.7717,2),(-41.6385,206.0148,4),(-89.438788,222.844980,2)]))
    with tempfile.TemporaryDirectory() as folder:
        td=Path(folder);source=rd.GeoTIFF('https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_83S_10MPP_ADJ.TIF');m=source.meta;c=m['width']//2;r=m['height']//2;a=source.read_window(c,r,8,8);path=td/'original.tif'
        with path.open('wb') as f:
            f.truncate(source.file.total)
            for off,raw in source.file.cache.items():f.seek(off);f.write(raw)
        with rasterio.open(path) as ds:assert np.array_equal(a,ds.read(1,window=Window(c,r,8,8)),equal_nan=True)
        print('BigTIFF/GDAL PASS',flush=True)
        packs=[]
        for i,west in enumerate((-128,0)):
            x=west+np.arange(192)+.5;y=64-np.arange(128)-.5;a=(1000+.25*x[None,:]+.5*y[:,None]).astype(np.float32);path=td/f'plane{i}.npz'
            dem.save_pack(path,a,dict(title='plane',projection='eqc',west=west,north=64,pixel_m=1,posting_m=1,scale=1,blend_pixels=16));packs.append(dem.Raster(path))
        x=np.linspace(-32,96,1025);lat,lon=rd.unproject(packs[0].meta,x,np.zeros_like(x));z=np.zeros_like(x)
        for p in packs:h,w=p.sample(lat,lon);z=z*(1-w)+h*w
        error=float(np.max(abs(z-(1000+.25*x))));assert error<1e-4,error
        dem.save_pack(td/'nan.npz',np.full((128,192),np.nan,np.float32),dict(packs[0].meta,title='NoData'));assert not dem.Raster(td/'nan.npz').sample(lat,lon)[1].any()
        class IgnoredRange:
            status=200;headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def geturl(self):return 'https://example.org/large.tif'
            def read(self,*args):raise AssertionError('Read an unbounded response')
        with patch('urllib.request.urlopen',return_value=IgnoredRange()):
            try:rd.RangeFile('https://example.org/large.tif').read(0,16)
            except ValueError:pass
            else:raise AssertionError('Range refusal missing')
        try:rd.RangeFile('https://example.org/tif',{'used':0,'limit':1}).read(0,16)
        except OSError:pass
        else:raise AssertionError('Budget not enforced')
        assert catalog.best(20.1908,30.7717)==catalog.best(20.1908,-329.2283)
        assert abs(catalog.best(0,359.99)['posting_m']-rd.MPD/4096)<1e-8
        pole=dem.TerrainDEM(-90,0);assert np.ptp(pole.height(np.array([-.1,.1,-1,1]),np.zeros(4)))<1
        p=next(catalog.jaxa_tiles(20.1908,30.7717,100));budget={'used':0,'limit':40*1024**2}
        for _,msg in dem_download.native_source(p,20.1908,30.7717,100,td,budget):pass
        j=next(dem.Raster(p) for p in td.glob('native_*.npz'));h,w=j.sample(np.array([20.1908]),np.array([30.7717]));assert w[0]==1 and abs(h[0]+2633)<.01 and abs(j.posting-rd.MPD/4096)<1e-8
        result=dict(passed=True,sites=rows,bigtiff_predictor3_gdal_exact=True,affine_seam_error_m=error,nodata_fallback=True,range_refusal=True,budget_enforced=True,pole_longitude_checks=True,jaxa_grid_m=j.posting,jaxa_bytes=budget['used'],jaxa_origin_elevation_m=float(h[0]))
        (ROOT/'tests/native_dem_results.json').write_text(json.dumps(result,indent=2));print('NATIVE DEM PASS',result,flush=True)
if __name__=='__main__':run()
