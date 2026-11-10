"""Build a close-up study of the actual generated rock geometry and material."""
from pathlib import Path
import bpy, sys, os, json
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import lunar_terrain as addon
from lunar_terrain import builder, rocks

def run():
    bpy.ops.wm.read_factory_settings(use_empty=True);addon.register()
    s=bpy.context.scene;p=s.lunar_terrain
    p.site='CE6';bpy.ops.lunar.apply_preset()
    p.outer_radius=100;p.detail_radius=10;p.mesh_spacing=.12
    p.rock_coverage=.179;p.micro_density=8;p.crater_density=.1;p.micro_craters=.1
    p.sun_azimuth=240;p.sun_elevation=24;p.samples=48
    job=builder.Build(s,addon.snapshot(p),addon.cache_path())
    for step in job.steps():print(step,flush=True)
    prototypes=next(c for c in bpy.data.collections if 'rock prototypes' in c.name)
    rows=[]
    for obj in prototypes.objects:
        me=obj.data;v=np.empty((len(me.vertices),3),np.float32);me.vertices.foreach_get('co',v.ravel())
        assert np.isfinite(v).all() and abs(rocks.hull_area(v[:,:2])-np.pi/4)<1e-6
        assert me.materials and not me.validate(verbose=True)
        rows.append(dict(index=obj['lunar_prototype_index'],vertices=len(me.vertices),triangles=len(me.polygons)))
    for i,(x,y,d) in enumerate([(0,0,1.5),(1.03,.70,.64),(-.85,.55,.27)]):
        source=next(o for o in prototypes.objects if o['lunar_prototype_index']==i)
        obj=source.copy();obj.name=f'Rock study {d:g} m';s.collection.objects.link(obj)
        obj.scale=(d,d,d);obj.location=(x,y,float(job.surface.height(x,y))-.07*d)
        obj.rotation_euler[2]=i*1.3
    cam=s.camera;cam.location=(1.7,-3.0,1.42)
    target=Vector((.0,.12,.26));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=62
    s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100
    s.render.threads_mode='FIXED';s.render.threads=8;s.cycles.samples=48
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
    s.render.filepath='//renders/Rock_Detail.png'
    s['lunar_material_version']='1.2.0';s['validated_blender']=bpy.app.version_string
    bpy.data.texts.new('START_HERE.md').write((ROOT/'README.md').read_text())
    bpy.data.texts.new('ROCK_STUDY.md').write('Artist-authored 1.5 m, 0.64 m and 0.27 m rocks using the same prototypes and Hapke material as the terrain generator. Placement is for inspection, not a measured boulder location. Fine textures use world metre coordinates.\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'examples/Rock_Detail.blend'),compress=True)
    bpy.ops.render.render(write_still=True)
    result=dict(blender=bpy.app.version_string,passed=True,prototypes=rows,projected_area_normalized=True,finite_vertices=True,valid_meshes=True)
    (ROOT/'tests/rock_detail_results.json').write_text(json.dumps(result,indent=2))

if __name__=='__main__':
    try:run()
    except Exception:
        import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush()
        if not bpy.app.binary_path:os._exit(1)
        raise
    sys.stdout.flush();sys.stderr.flush()
    if not bpy.app.binary_path:os._exit(0)
