"""Open and render delivered scenes without importing/registering the add-on."""
from pathlib import Path
import bpy, json, sys, os, tempfile
ROOT=Path(__file__).resolve().parents[1]

def run():
    reports=[]
    with tempfile.TemporaryDirectory() as tmp:
        for name in ('Apollo17_Surface','Apollo17_Outpost','ChangE6_Surface','Rock_Detail'):
            assert not hasattr(bpy.types.Scene,'lunar_terrain')
            bpy.ops.wm.open_mainfile(filepath=str(ROOT/'examples'/(name+'.blend')))
            scene=bpy.context.scene
            assert bpy.data.version[:2]==(5,2), bpy.data.version
            assert scene.camera and scene.world and 'START_HERE.md' in bpy.data.texts
            assert len(bpy.data.libraries)==0
            assert not [im for im in bpy.data.images if im.source=='FILE' and not im.packed_file]
            prototypes=[c for c in bpy.data.collections if 'rock prototypes' in c.name]
            assert len(prototypes)==1 and len(prototypes[0].objects)==24
            scene.render.resolution_percentage=20;scene.cycles.samples=8
            scene.render.threads_mode='FIXED';scene.render.threads=4
            scene.render.filepath=str(Path(tmp)/(name+'.png'))
            bpy.ops.render.render(write_still=True)
            assert Path(scene.render.filepath).stat().st_size>2000
            drivers=[]
            for container in (bpy.data.materials,bpy.data.worlds,bpy.data.node_groups):
                for block in container:
                    tree=block if isinstance(block,bpy.types.NodeTree) else getattr(block,'node_tree',None)
                    if tree and tree.animation_data:
                        drivers.extend(tree.animation_data.drivers)
            assert drivers and all(fc.driver.is_valid for fc in drivers)
            reports.append(dict(scene=name,blender=bpy.app.version_string,saved_blend_version=list(bpy.data.version),standalone_render=True,valid_drivers=len(drivers),external_dependencies=0))
            print('PORTABILITY PASS',reports[-1],flush=True)
    (ROOT/'tests/portability_results.json').write_text(json.dumps(reports,indent=2))

if __name__=='__main__':
    try:run()
    except Exception:
        import traceback
        traceback.print_exc();sys.stdout.flush();sys.stderr.flush()
        if not bpy.app.binary_path:os._exit(1)
        raise
    sys.stdout.flush();sys.stderr.flush()
    if not bpy.app.binary_path:os._exit(0)
