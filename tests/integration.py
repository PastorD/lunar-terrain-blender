"""Run with Blender 5.2 background Python. No third-party testing framework needed."""
from pathlib import Path
import sys, json, tempfile, os, math
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
import lunar_terrain as addon
from lunar_terrain import dem, builder, surface

def run():
    results = {'blender': bpy.app.version_string, 'checks': []}
    def ok(name, **values):
        results['checks'].append(dict(name=name, passed=True, **values))
        print('PASS:', name, values, flush=True)
    def consume(g):
        while True:
            try: next(g)
            except StopIteration as e: return e.value

    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon.register(); addon.unregister(); addon.register()
    scene = bpy.context.scene; p = scene.lunar_terrain
    ok('register / unregister / register')

    for lat, lon, expected in [(20.1908,30.7717,-2627.5012),(-89.438788,222.844980,1959.16288)]:
        d = dem.TerrainDEM(lat,lon)
        assert abs(d.h0-expected)<.05, (d.h0, expected)
        assert abs(float(d.height(0,0)))<1e-6
        ok('DEM origin and units', latitude=lat, elevation_m=d.h0)
    for lat in (-90,90):
        d=dem.TerrainDEM(lat, 0)
        values=d.height(np.array([0,.1,1.,-.1,-1.]),np.zeros(5))
        assert np.ptp(values)<1
        ok('exact pole continuity',latitude=lat,range_m=float(np.ptp(values)))
    a=dem.TerrainDEM(0,359.99); b=dem.TerrainDEM(0,-.01)
    assert abs(a.h0-b.h0)<1e-8
    ok('longitude wrapping')

    class BadResponse:
        status=200; headers={}
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self,*args): raise AssertionError('Full response body must not be read')
    with patch.object(dem.urllib.request,'urlopen',return_value=BadResponse()):
        try: dem._strip('https://example.com/dem',0,99,1000)
        except OSError: pass
        else: raise AssertionError('Ignored HTTP range was accepted')
    ok('range-ignored download refuses full body')

    user=bpy.data.objects.new('User retained object',None); scene.collection.objects.link(user)
    userworld=bpy.data.worlds.new('Original user world'); scene.world=userworld
    usercamera=bpy.data.objects.new('Original user camera',bpy.data.cameras.new('User camera'))
    scene.collection.objects.link(usercamera); scene.camera=usercamera
    p.outer_radius=300; p.detail_radius=12; p.mesh_spacing=.25
    p.micro_density=1; p.micro_craters=.1; p.samples=8
    assert bpy.ops.lunar.build()=={'FINISHED'}
    owner=p.last_owner
    ground=next(o for o in scene.objects if o.type=='MESH' and 'Joined multiresolution' in o.data.name)
    me=ground.data
    verts=np.empty((len(me.vertices),3),np.float32); me.vertices.foreach_get('co',verts.ravel())
    faces=np.empty((len(me.polygons),3),np.int32); me.loops.foreach_get('vertex_index',faces.ravel())
    edges=np.sort(np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]])),axis=1)
    unique,counts=np.unique(edges,axis=0,return_counts=True)
    assert counts.max()==2
    boundary=unique[counts==1]
    assert np.allclose(np.linalg.norm(verts[boundary,:2],axis=2),300,atol=.001)
    assert len(verts)-len(unique)+len(faces)==1
    a=verts[faces[:,1],:2]-verts[faces[:,0],:2]
    b=verts[faces[:,2],:2]-verts[faces[:,0],:2]
    assert np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])>0
    ok('continuous mesh; only outer boundary; consistent winding',vertices=len(verts),triangles=len(faces),boundary_edges=len(boundary))

    saved_objects=set(bpy.data.objects)
    job=builder.Build(scene,addon.snapshot(p),addon.cache_path()); g=job.steps(); next(g); g.close()
    assert set(bpy.data.objects)==saved_objects and p.last_owner==owner
    ok('cancelled staging retains completed scene')
    cfg=addon.snapshot(p); cfg.max_rocks=1
    job=builder.Build(scene,cfg,addon.cache_path())
    try: consume(job.steps())
    except ValueError: pass
    else: raise AssertionError('Expected instance budget error')
    assert set(bpy.data.objects)==saved_objects and p.last_owner==owner
    ok('late build failure removes staged data and retains completed scene')

    root=next(c for c in scene.collection.children if c.get('_lunar_root'))
    addition=bpy.data.objects.new('User object inside generated collection',None); root.objects.link(addition)
    camera=scene.camera; camera.location=(42,-18,3); camera.data.lens=75
    bpy.context.view_layer.update(); transform=camera.matrix_world.copy()
    p.focus_mode='CAMERA'; p.rock_coverage=0; p.micro_density=0; p.crater_density=0; p.micro_craters=0
    assert bpy.ops.lunar.build()=={'FINISHED'}
    bpy.context.view_layer.update()
    assert addition.name in scene.objects and user.name in scene.objects
    camera_error=float(np.max(np.abs(np.asarray(scene.camera.matrix_world)-np.asarray(transform))))
    assert camera_error<1e-6 and scene.camera.data.lens==75, (camera_error,scene.camera.data.lens)
    assert json.loads(p.stats)['detail_focus_xy_m']==[42.,-18.]
    assert json.loads(p.stats)['rocks']==0 and json.loads(p.stats)['craters']==0
    ok('camera focus, zero populations and user object preservation')

    # A world-only raw render makes angular size and camera visibility measurable.
    for o in scene.objects:
        if o.type not in ('LIGHT','CAMERA'): o.hide_render=True
    sun=next(o for o in scene.objects if o.type=='LIGHT' and o.data.type=='SUN')
    look=next(o for o in scene.objects if 'look at Sun' in o.name)
    scene.camera=look; scene.render.resolution_x=256; scene.render.resolution_y=256
    scene.render.resolution_percentage=100; scene.render.threads_mode='FIXED'; scene.render.threads=4
    scene.cycles.samples=16; scene.cycles.use_denoising=False
    scene.render.image_settings.file_format='OPEN_EXR'; scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.color_depth='32'
    with tempfile.TemporaryDirectory() as tmp:
        def render(name):
            path=Path(tmp)/(name+'.exr'); scene.render.filepath=str(path)
            scene.frame_set(scene.frame_current+1); bpy.context.view_layer.update()
            bpy.ops.render.render(write_still=True)
            image=bpy.data.images.load(str(path),check_existing=False)
            a=np.asarray(image.pixels[:],np.float32).reshape(256,256,4)[:,:,:3].max(axis=2)
            bpy.data.images.remove(image); return a
        pixels=render('sun')
        assert pixels.max()>500
        yy,xx=np.where(pixels>500)
        assert 124 < xx.mean() < 131 and 124 < yy.mean() < 131
        diameter=2*math.sqrt(float((pixels/1000).sum())/math.pi)
        assert 5.5<diameter<7.7
        sun.rotation_euler=builder.direction(p.sun_azimuth+180,-p.sun_elevation).to_track_quat('Z','Y').to_euler()
        away=render('away'); assert away.max()<1e-5
        ok('visible solar disc follows Sun and black sky elsewhere',effective_diameter_pixels=diameter,peak_linear=float(pixels.max()))

    bpy.ops.lunar.clear()
    assert scene.camera==usercamera and scene.world==userworld
    assert user.name in scene.objects and addition.name in scene.objects
    assert not any(o.get(builder.OWNER) for o in bpy.data.objects)
    ok('clear restores original camera/world and retains user objects')
    addon.unregister()
    results['all_passed']=True
    (ROOT/'tests'/'results.json').write_text(json.dumps(results,indent=2))
    print('ALL INTEGRATION CHECKS PASSED',flush=True)

if __name__=='__main__':
    try: run()
    except Exception:
        import traceback
        traceback.print_exc(); sys.stdout.flush(); sys.stderr.flush()
        if not bpy.app.binary_path: os._exit(1)
        raise
    sys.stdout.flush(); sys.stderr.flush()
    if not bpy.app.binary_path: os._exit(0)
