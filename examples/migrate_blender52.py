"""Upgrade existing examples in place and render them in Blender 5.2.

Terrain, rock placements, cameras, photometric values and exposure are checked
for preservation. Owned rock prototype geometry/materials are upgraded.
"""
from pathlib import Path
import bpy, sys, os, json, hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import lunar_terrain as addon
from lunar_terrain import builder, hapke, rocks

def terrain_signature(scene):
    rows={}
    for obj in scene.objects:
        if obj.type!='MESH':continue
        me=obj.data;a=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',a)
        rows[obj.name]=(me.as_pointer(),len(me.polygons),hashlib.sha256(a.tobytes()).hexdigest())
    return rows

def run():
    assert bpy.app.version[:2]==(5,2)
    addon.register();rows=[]
    for name in ('Apollo17_Surface','Apollo17_Outpost','ChangE6_Surface'):
        file=ROOT/'examples'/(name+'.blend');bpy.ops.wm.open_mainfile(filepath=str(file))
        source_version=list(bpy.data.version)
        s=bpy.context.scene;p=s.lunar_terrain;before=terrain_signature(s)
        camera=s.camera;camera_matrix=tuple(tuple(row) for row in camera.matrix_world)
        exposure=s.view_settings.exposure
        sun=next(o for o in s.objects if o.type=='LIGHT' and o.data.type=='SUN')
        light=(tuple(sun.rotation_euler),sun.data.energy)
        material_inputs={m.name:{k:m.node_tree.nodes['HAPKE_CONTROLS'].inputs[k].default_value for k in hapke.DEFAULTS}
                         for m in bpy.data.materials if m.node_tree and 'HAPKE_CONTROLS' in m.node_tree.nodes}
        changed=builder.upgrade_rocks(s,addon.snapshot(p))
        assert before==terrain_signature(s) and s.camera==camera
        assert camera_matrix==tuple(tuple(row) for row in s.camera.matrix_world)
        assert light==(tuple(sun.rotation_euler),sun.data.energy) and exposure==s.view_settings.exposure
        for name_,inputs in material_inputs.items():
            node=bpy.data.materials[name_].node_tree.nodes['HAPKE_CONTROLS']
            assert all(abs(node.inputs[k].default_value-v)<1e-7 for k,v in inputs.items())
        assert builder.upgrade_rocks(s,addon.snapshot(p))==0
        prot=next(c for c in bpy.data.collections if 'rock prototypes' in c.name)
        assert len(prot.objects)==24 and all(o.data.get('lunar_rock_schema')==rocks.SCHEMA for o in prot.objects)
        for doc in ('README.md','APPEARANCE_UPDATE.md','BLENDER_52_UPDATE.md'):
            key='START_HERE.md' if doc=='README.md' else doc
            t=bpy.data.texts.get(key) or bpy.data.texts.new(key);t.clear();t.write((ROOT/doc).read_text())
        s['lunar_material_version']='1.2.0';s['validated_blender']=bpy.app.version_string
        s.render.threads_mode='FIXED';s.render.threads=8;s.render.resolution_percentage=100
        s.cycles.samples=48;s.cycles.use_denoising=True
        s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='8'
        s.render.filepath='//renders/'+name+'.png'
        bpy.ops.wm.save_as_mainfile(filepath=str(file),compress=True)
        bpy.ops.render.render(write_still=True)
        rows.append(dict(scene=name,source_blend_version=source_version,blender=bpy.app.version_string,
                         prototypes_upgraded=changed,terrain_placements_camera_sun_photometry_exposure_preserved=True,
                         idempotent=True,resolution=[s.render.resolution_x,s.render.resolution_y],cycles_samples=48,passed=True))
        (ROOT/'tests/migration_results.json').write_text(json.dumps(rows,indent=2))
        print('MIGRATION AND RENDER PASS',rows[-1],flush=True)

if __name__=='__main__':
    try:run()
    except Exception:
        import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush()
        if not bpy.app.binary_path:os._exit(1)
        raise
    sys.stdout.flush();sys.stderr.flush()
    if not bpy.app.binary_path:os._exit(0)
