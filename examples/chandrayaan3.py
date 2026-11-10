"""Build the Chandrayaan-3 reference study with actual terrain and Cycles.

blender -b --python examples/chandrayaan3.py
python examples/chandrayaan3.py --draft  # official bpy wheel
Use --reuse to reopen the saved study and apply the current appearance values.
"""
from pathlib import Path
import argparse
import json
import os
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
import numpy as np
import lunar_terrain as addon


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--reuse', action='store_true')
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    addon.register()
    blend = ROOT / 'examples/Chandrayaan3_Surface.blend'
    if args.reuse:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        p = bpy.context.scene.lunar_terrain
        p.appearance = 'CH3'
        assert bpy.ops.lunar.apply_appearance() == {'FINISHED'}
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        p = bpy.context.scene.lunar_terrain
        p.site = 'CH3'
        assert bpy.ops.lunar.apply_preset() == {'FINISHED'}
        p.download_first = False
        p.detail_radius = 24
        p.mesh_spacing = .12
        p.include_outpost = False
        assert bpy.ops.lunar.build() == {'FINISHED'}
    scene = bpy.context.scene
    report = json.loads(p.stats)
    assert report['rocks'] > 0 and report['craters'] > 0
    assert abs(min(v['posting_m'] for v in report['dem_resolution']['loaded_at_origin']) - 3.) < 1e-8
    # Applying an appearance must keep the user's terrain, Sun and camera.
    meshes = {o.name: o.data.as_pointer() for o in scene.objects if o.type == 'MESH'}
    camera = scene.camera
    camera_matrix = camera.matrix_world.copy()
    sun = next(o for o in scene.objects if o.type == 'LIGHT' and o.data.type == 'SUN')
    sun_matrix = sun.matrix_world.copy()
    for look in ('APOLLO', 'CHANGE', 'BLUEGHOST', 'CH3'):
        p.appearance = look
        assert bpy.ops.lunar.apply_appearance() == {'FINISHED'}
        assert meshes == {o.name: o.data.as_pointer() for o in scene.objects if o.type == 'MESH'}
        assert camera == scene.camera and camera_matrix == camera.matrix_world
        assert sun_matrix == sun.matrix_world
        expected_gain = 2.2 if look == 'CH3' else 1.0
        assert abs(p.regolith_relief - expected_gain) < 1e-6
        for mat in bpy.data.materials:
            if mat.get(addon.builder.OWNER) == p.last_owner and not mat.get('lunar_rock') and mat.node_tree:
                bump = mat.node_tree.nodes.get('METRIC_RELIEF')
                if bump: assert abs(bump.inputs['Distance'].default_value - .012 * expected_gain) < 1e-7
    prior = addon.appearance.parameters_at(p.latitude, p.longitude)
    assert abs(p.single_scattering_albedo - prior['w']) < 1e-6
    assert p.cboe_amplitude == 0 and p.opposition == 1
    material_count = 0
    for mat in bpy.data.materials:
        if mat.get(addon.builder.OWNER) == p.last_owner and mat.node_tree and mat.node_tree.nodes.get('HAPKE_CONTROLS'):
            material_count += 1
    assert material_count >= 2, 'Both regolith and rocks need the new appearance'
    scene['lunar_material_version'] = tomllib.loads((ROOT / 'lunar_terrain/blender_manifest.toml').read_text())['version']
    scene['reference_study'] = 'Chandrayaan-3 photographs: artistic colour/exposure/framing; regional LROC Hapke prior'
    for filename in ('README.md', 'CHANDRAYAAN3.md'):
        if (ROOT / filename).exists():
            text = bpy.data.texts.get(filename) or bpy.data.texts.new(filename)
            text.clear()
            text.write((ROOT / filename).read_text())
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 8
    scene.render.resolution_x, scene.render.resolution_y = (768, 768) if args.draft else (1024, 1024)
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 24 if args.draft else 64
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    (ROOT / 'examples/renders').mkdir(exist_ok=True)
    scene.render.filepath = '//renders/Chandrayaan3_Surface.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    bpy.ops.render.render(write_still=True)
    result = dict(passed=True, blender=bpy.app.version_string,
                  preset='CH3', coordinates=[p.latitude,p.longitude],
                  photometry=prior, appearance=addon.appearance.LOOKS['CH3'],
                  sun_elevation=p.sun_elevation, sun_azimuth=p.sun_azimuth,
                  camera_heading=p.camera_heading, camera_pitch=p.camera_pitch,
                  camera_lens_mm=p.camera_lens, camera_height_m=p.camera_height,
                  mesh_and_camera_preserved_by_appearance=True,
                  hapke_materials=material_count, generation=report,
                  render_size=[scene.render.resolution_x,scene.render.resolution_y],
                  samples=scene.cycles.samples, scope='Official Linux bpy 5.2.1; headless CPU Cycles')
    (ROOT / 'tests/chandrayaan3_results.json').write_text(json.dumps(result, indent=2))
    print('CHANDRAYAAN-3 STUDY PASS', report['triangles'], 'triangles;', report['rocks'], 'rocks', flush=True)


if __name__ == '__main__':
    code = 0
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    if not bpy.app.binary_path:
        os._exit(code)
    if code:
        raise SystemExit(code)
