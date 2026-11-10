"""Build native terrains through public Blender operators and verify reported data."""
from pathlib import Path
import sys,os,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import bpy,numpy as np,lunar_terrain as addon
def run():
    assert bpy.app.version[:2]==(5,2);bpy.ops.wm.read_factory_settings(use_empty=True);addon.register()
    bpy.ops.mesh.primitive_cube_add();user=bpy.context.object;user.name='User geometry retained';rows=[]
    for site,want in [('APOLLO17',2),('CE6',4),('SOUTH',2)]:
        p=bpy.context.scene.lunar_terrain;p.site=site;bpy.ops.lunar.apply_preset();p.download_first=False;p.outer_radius=300;p.detail_radius=12;p.mesh_spacing=.35;p.include_outpost=False;p.rock_coverage=0;p.micro_density=0;p.crater_density=0;p.micro_craters=0
        assert bpy.ops.lunar.build()=={'FINISHED'};report=json.loads(p.stats);assert user.name in bpy.data.objects
        assert abs(min(r['posting_m'] for r in report['dem_resolution']['loaded_at_origin'])-want)<1e-8
        for o in bpy.data.objects:
            if o.type=='MESH':
                a=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);assert np.isfinite(a).all()
        rows.append(dict(site=site,triangles=report['triangles'],dem=report['dem_resolution'],passed=True))
    p.latitude=0;assert p.dem_report=='{}' and p.dem_download_report=='{}' and 'changed' in p.dem_status
    assert bpy.ops.lunar.inspect_dem()=={'FINISHED'} and 'Cached' in p.dem_status
    bpy.ops.lunar.clear();assert user.name in bpy.data.objects;addon.unregister();addon.register();addon.unregister()
    result=dict(passed=True,blender=bpy.app.version_string,sites=rows,stale_reports_cleared=True,user_geometry_retained=True,scope='Official Linux bpy 5.2.1, headless CPU; no interactive Blender UI or GPU validation')
    (ROOT/'tests/blender_dem_results.json').write_text(json.dumps(result,indent=2));print('BLENDER DEM PASS',flush=True)
if __name__=='__main__':
    code=0
    try:run()
    except Exception:
        import traceback;traceback.print_exc();code=1
    sys.stdout.flush();sys.stderr.flush();os._exit(code)
