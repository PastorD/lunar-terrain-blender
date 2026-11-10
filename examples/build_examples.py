"""Blender 5.2: blender -b --python examples/build_examples.py"""
from pathlib import Path
import sys, json, os
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
import lunar_terrain

def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lunar_terrain.register()
    scene = bpy.context.scene
    p = scene.lunar_terrain
    p.site = 'APOLLO17'
    bpy.ops.lunar.apply_preset()
    (ROOT / 'examples' / 'renders').mkdir(exist_ok=True)
    readme = bpy.data.texts.new('START_HERE.md')
    readme.write((ROOT / 'README.md').read_text())
    reports = {}
    for name, outpost, width, height, samples in [
        ('Apollo17_Surface', False, 1100, 1100, 48),
        ('Apollo17_Outpost', True, 1800, 1100, 64),
    ]:
        p.include_outpost = outpost
        p.sun_azimuth = 230 if outpost else 300
        p.samples = samples
        assert bpy.ops.lunar.build() == {'FINISHED'}
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = 8
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.filepath = '//renders/' + name + '.png'
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'examples' / (name + '.blend')), compress=True)
        bpy.ops.render.render(write_still=True)
        reports[name] = json.loads(p.stats)
        print('EXAMPLE COMPLETE:', name, reports[name], flush=True)
    (ROOT / 'examples' / 'generation_reports.json').write_text(json.dumps(reports, indent=2))
    print('ALL EXAMPLES COMPLETE', flush=True)

if __name__ == '__main__':
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.stdout.flush(); sys.stderr.flush()
        if not bpy.app.binary_path: os._exit(1)
        raise
    sys.stdout.flush(); sys.stderr.flush()
    # bpy wheel has a known shutdown hang in this headless host; real Blender exits normally.
    if not bpy.app.binary_path: os._exit(0)
