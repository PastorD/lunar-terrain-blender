"""Bundle native crops at the presets without elevation resampling."""
from pathlib import Path
import sys,types,json
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('lunar_terrain');pkg.__path__=[str(ROOT/'lunar_terrain')];sys.modules['lunar_terrain']=pkg
from lunar_terrain import catalog,dem,dem_download
def run(site):
    name,lat,lon=site;p=catalog.best(lat,lon);budget={'used':0,'limit':512*1024**2}
    for _,message in dem_download.native_source(p,lat,lon,2200,dem.DATA,budget):print(name,message,flush=True)
    d=dem.TerrainDEM(lat,lon);result=dict(site=name,download_bytes=budget['used'],h0_m=d.h0,report=d.resolution_report(20000))
    (ROOT/'tests'/('download_'+name+'.json')).write_text(json.dumps(result,indent=2))
    print('DONE',name,d.h0,flush=True);return result
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,[('Apollo17',20.1908,30.7717),('ChangE6',-41.6385,206.0148),('ConnectingRidge',-89.438788,222.844980),('BlueGhost',18.5623,61.8103),('Chandrayaan3',-69.373,32.319)]))
    (ROOT/'tests/native_download_results.json').write_text(json.dumps(rows,indent=2))
