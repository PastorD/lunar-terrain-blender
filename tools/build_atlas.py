"""Build standalone HTML and optional real DEM polar context map."""
from pathlib import Path
import argparse,json,sys,types
ROOT=Path(__file__).resolve().parents[1]
def build(polar=False):
    data=json.loads((ROOT/'docs/atlas-data.json').read_text())
    assert len(data['sites'])==len({s['id'] for s in data['sites']})==8
    html=(ROOT/'docs/atlas-template.html').read_text().replace('__ATLAS_DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c'))
    for file in ('docs/index.html','lunar_terrain/data/Lunar_Atlas.html'):(ROOT/file).write_text(html,encoding='utf-8')
    if polar:
        import numpy as np
        from PIL import Image
        module=types.ModuleType('lunar_terrain');module.__path__=[str(ROOT/'lunar_terrain')];sys.modules['lunar_terrain']=module
        from lunar_terrain import dem
        terrain=dem.TerrainDEM(-90,0);size=800;extent=2*dem.RADIUS*np.tan(np.radians(5));axis=(np.arange(size)+.5)/size*2-1
        x,y=np.meshgrid(axis*extent,-axis*extent);rho=np.hypot(x,y)
        lat=-90+np.degrees(2*np.arctan(rho/(2*dem.RADIUS)));lon=np.degrees(np.arctan2(x,y))%360
        z=terrain.elevation(lat.ravel(),lon.ravel()).reshape(size,size);dy,dx=np.gradient(z,2*extent/size)
        shade=(dx*.5-dy*.5+2**-.5)/np.sqrt(1+dx*dx+dy*dy);v=np.clip(.18+.72*shade,0,1)
        rgba=np.stack([v*.85,v*.90,v,(rho<=extent)],axis=-1)
        out=ROOT/'build/atlas/Polar_Context.png';out.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(np.uint8(rgba*255)).save(out)
    print('LUNAR ATLAS BUILT',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--polar-map',action='store_true');build(p.parse_args().polar_map)
