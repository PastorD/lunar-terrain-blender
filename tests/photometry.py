"""Render a controlled opposition sweep and compare linear on/off ratios.

The same Hapke node builder is used in the outpost and diagnostic scenes.
Normal-incidence Sun; orthographic camera at phase/emergence = 0..60 degrees.
Only the opposition terms change between the two panels.
"""
import bpy,math,sys,json,csv
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lunar_terrain import hapke

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.name='Hapke • controlled opposition check'
    scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=False
    scene.cycles.max_bounces=1;scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
    world=bpy.data.worlds.new('Black');scene.world=world
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
    sd=bpy.data.lights.new('Diagnostic collimated Sun','SUN');sd.energy=1;sd.angle=0
    sun=bpy.data.objects.new('Diagnostic Sun',sd);scene.collection.objects.link(sun)
    group=hapke.build_group(sun)
    for x,name,strength in [(-2,'Opposition ON',1),(2,'Opposition OFF',0)]:
        ma=bpy.data.materials.new(name);n=ma.node_tree.nodes;n.clear()
        g=n.new('ShaderNodeGroup');g.node_tree=group;g.inputs['Normal'].default_value=(0,0,1)
        g.inputs['Tint'].default_value=(1,1,1,1);g.inputs['Opposition strength'].default_value=strength
        out=n.new('ShaderNodeOutputMaterial');ma.node_tree.links.new(g.outputs['BSDF'],out.inputs['Surface'])
        mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x-1.5,-4,0),(x+1.5,-4,0),(x+1.5,4,0),(x-1.5,4,0)],[],[(0,1,2,3)])
        obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);mesh.materials.append(ma)
    cd=bpy.data.cameras.new('Phase sweep camera');cam=bpy.data.objects.new('Phase sweep camera',cd)
    scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=8.4
    rows=[]
    for alpha in [0,.25,10,60]:
        a=math.radians(alpha);cam.location=(0,-20*math.sin(a),20*math.cos(a))
        # Explicit Euler rotation avoids the look-at roll singularity at zero phase.
        cam.rotation_euler=(a,0,0)
        scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_depth='32'
        path=ROOT/'examples'/'renders'/f'_phase_{alpha:g}.exr';scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        im=bpy.data.images.load(str(path),check_existing=False)
        arr=np.array(im.pixels[:],dtype=float).reshape(360,640,4)
        on=float(arr[160:200,150:185,:3].mean());off=float(arr[160:200,455:490,:3].mean())
        ratio=on/off
        expected=hapke.analytic(alpha,0,alpha)/hapke.analytic(alpha,0,alpha,opposition=0)
        row=dict(phase_deg=alpha,linear_on=on,linear_off=off,render_ratio=ratio,analytic_ratio=expected,
                 relative_error=abs(ratio-expected)/expected)
        rows.append(row);bpy.data.images.remove(im);path.unlink()
        # Save a display image of each comparison with the same exposure.
        scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_depth='8'
        bpy.data.images['Render Result'].save_render(str(ROOT/'examples'/'renders'/f'Opposition_{alpha:g}deg.png'),scene=scene)
        print('PHOTOMETRY',row,flush=True)
    with (ROOT/'tests/opposition_validation.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result=dict(blender=bpy.app.version_string,test='Identical planar panels, constant normal-incidence Sun, orthographic emergence/phase sweep',
        max_relative_ratio_error=max(r['relative_error'] for r in rows),
        passed=all(r['relative_error']<.02 for r in rows),rows=rows,
        limits='Tests this node implementation against its stated approximation; does not validate parameters against lunar photometric measurements.')
    (ROOT/'tests/photometry_validation.json').write_text(json.dumps(result,indent=2))
    cam.location=(0,0,20);cam.rotation_euler=(0,0,0)
    scene.render.filepath='//renders/Opposition_0deg.png'
    bpy.data.texts.new('DIAGNOSTIC_README').write('Left: opposition ON. Right: OFF. Same material parameters, normal and illumination.\nCamera at the Sun direction: zero phase. Rotate the camera around the origin to vary phase.\nSee opposition_validation.csv for the rendered, linear-light test sweep.\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'examples/Hapke_Opposition_Check.blend'),compress=True)
    if not result['passed']:raise RuntimeError('Photometry ratio mismatch: inspect implementation.')

if __name__=='__main__':
    try: main()
    except Exception:
        import traceback,os
        traceback.print_exc();sys.stdout.flush();sys.stderr.flush()
        if not bpy.app.binary_path:os._exit(1)
        raise
    sys.stdout.flush();sys.stderr.flush()
    if not bpy.app.binary_path:
        import os
        os._exit(0)
