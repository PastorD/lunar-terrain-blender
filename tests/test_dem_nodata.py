"""A missing-data boundary must blend into the coarser measured elevation."""
from pathlib import Path
import sys,types,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];package=types.ModuleType('lunar_terrain');package.__path__=[str(ROOT/'lunar_terrain')];sys.modules['lunar_terrain']=package
from lunar_terrain import dem
with tempfile.TemporaryDirectory() as directory:
    a=np.full((96,96),100.,np.float32);a[:,40:56]=np.nan;path=Path(directory)/'hole.npz'
    dem.save_pack(path,a,dict(title='Synthetic regression grid',projection='cylindrical',west=0.,north=48.,ppd=1.,posting_m=1.,scale=1.,blend_pixels=2.))
    r=dem.Raster(path);lon=np.linspace(22,80,581);lat=np.zeros_like(lon);z,w=r.sample(lat,lon);combined=10*(1-w)+z*w
    assert np.isfinite(combined).all() and np.all(combined[(lon>43)&(lon<52)]==10)
    assert np.any((w>0)&(w<1)) and abs(np.diff(combined)).max()<1.2
    assert np.allclose(combined[lon>76],100)
print('DEM NO-DATA FEATHER PASS')
