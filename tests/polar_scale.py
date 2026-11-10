"""Independent PROJ regression for true-scale polar PDS maps. Developer-only pyproj."""
from pathlib import Path
import sys,types,json
import numpy as np
from pyproj import Proj
ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('lunar_terrain');pkg.__path__=[str(ROOT/'lunar_terrain')];sys.modules['lunar_terrain']=pkg
from lunar_terrain import remote_dem as rd,dem
rows=[]
for south,ts,lon0 in [(True,-69.3,32.3),(True,-90,0),(False,72.5,359),(False,90,0)]:
 m=dict(projection='south_polar' if south else 'north_polar',standard_parallel=ts,central_longitude=lon0)
 lat=np.array([60,69.373,80,89.99,90])*(-1 if south else 1);lon=np.array([32.319,31.31,33.37,359.9,0])
 ref=Proj(proj='stere',lat_0=-90 if south else 90,lat_ts=ts,lon_0=lon0,R=rd.RADIUS)
 x,y=rd.project(m,lat,lon);a,b=ref(lon,lat);error=float(np.max(np.hypot(x-a,y-b)));assert error<1e-6
 la,lo=rd.unproject(m,x,y);assert np.max(abs(la-lat))<1e-10;keep=abs(lat)<90;assert np.max(abs((lo[keep]-lon[keep]+180)%360-180))<1e-10
 rows.append(dict(south=south,true_scale_latitude=ts,central_longitude=lon0,max_error_m=error))
d=dem.TerrainDEM(-69.373,32.319);loaded=d.description()
assert any('VIKRAMSITE1' in v['title'] and abs(v['posting_m']-3)<1e-8 and v['centre_weight']==1 for v in loaded),loaded
assert 480<d.h0<580
result=dict(passed=True,reference='Independent PROJ via pyproj',coordinate_checks=rows,origin_elevation_m=d.h0,loaded=loaded)
(ROOT/'tests/polar_scale_results.json').write_text(json.dumps(result,indent=2));print('POLAR SCALE PASS',result,flush=True)
