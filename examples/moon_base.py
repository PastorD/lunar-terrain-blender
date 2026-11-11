"""Build the NASA Moon Base target-region terrain study (Blender 5.2.1).

blender -b --python examples/moon_base.py
python examples/moon_base.py --draft  # official bpy wheel
Use --reuse to render the existing geometry again. No network during generation.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
import numpy as np
from mathutils import Vector
import lunar_terrain as addon

LATITUDE, LONGITUDE = -89.4632, 222.51
RELEASE = 'moonbase-v1.0.0'
NAME = 'NASA_MoonBase_Connecting_Ridge'
CONTEXT = {
    'region': 'Shackleton Connecting Ridge',
    'mission': 'Blue Moon Mark 1 / early NASA Moon Base mission',
    'status_checked': '2026-11-10',
    'mission_schedule_at_check': '2027',
    'latitude': LATITUDE, 'longitude_east': LONGITUDE,
    'coordinate_role': 'NASA Lunar Surface Data Book Rev A, Table A2-2, R01 regional reference point; NOT a confirmed touchdown coordinate or landing ellipse',
    'base_site_status': 'NASA is studying several south-polar areas; this does not identify a finalized permanent Moon Base site',
    'mission_source': 'https://www.nasa.gov/event/clps-flight-blue-origins-blue-moon-mark-1/',
    'base_status_source': 'https://www.nasa.gov/moon-base-frequently-asked-questions/',
    'coordinate_source': 'https://ntrs.nasa.gov/citations/20230007818',
    'coordinate_table': 'ACD-50044 Rev A, Table A2-2, printed page 58',
    'photometry': 'Apollo 17 regional LROC Hapke analogue; polar location is outside the 70 S to 70 N parameter map',
    'lighting': 'Illustrative Sun azimuth 285 deg, elevation 1.4 deg; no dated ephemeris or landing-time prediction',
    'small_features': 'Procedural rocks, craterlets and regolith below DEM scale; not a mapped hazard population',
    'hardware': 'Terrain study only; no official lander or base architecture',
}


def horizon_report(dem):
    """Sample DEM-only horizon at eye height, including Moon curvature."""
    distances = np.unique(np.r_[np.arange(2., 102., 2.), np.geomspace(100, 20000, 500)])
    az = math.radians(285)
    elevations = dem.height(np.sin(az) * distances, np.cos(az) * distances)
    angles = np.degrees(np.arctan2(elevations - 1.8, distances))
    k = int(np.argmax(angles))
    return dict(azimuth_deg=285, horizon_elevation_deg=float(angles[k]),
                blocking_distance_m=float(distances[k]), eye_height_m=1.8,
                sun_centre_elevation_deg=1.4, solar_radius_deg=.265,
                sun_disc_above_sampled_horizon=bool(1.4 - .265 > angles[k]),
                extent_m=20000, includes_curvature=True,
                scope='Sampled radial DEM profile only; excludes sub-DEM features and occluders outside the 20 km mesh')


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--reuse', action='store_true')
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    addon.register()
    blend = ROOT / 'examples' / (NAME + '.blend')
    if args.reuse:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        p = bpy.context.scene.lunar_terrain
        p.site = 'SOUTH'
        assert bpy.ops.lunar.apply_preset() == {'FINISHED'}
        p.latitude, p.longitude = LATITUDE, LONGITUDE
        addon.appearance.apply(p, 'APOLLO')
        p.download_first = False
        p.outer_radius, p.detail_radius, p.mesh_spacing = 20000, 24, .12
        p.focus_mode, p.curvature = 'LOCATION', True
        p.seed = 20261110
        p.include_outpost = False
        p.sun_azimuth, p.sun_elevation, p.sun_diameter = 285, 1.4, .53
        p.camera_height, p.camera_heading, p.camera_pitch, p.camera_lens = 1.8, 5, -5, 32
        assert bpy.ops.lunar.build() == {'FINISHED'}
    scene = bpy.context.scene
    p = scene.lunar_terrain
    report = json.loads(p.stats)
    assert abs(report['latitude'] - LATITUDE) < 1e-4
    assert abs(report['longitude_east'] - LONGITUDE) < 1e-4
    assert p.curvature and report['outer_radius_m'] == 20000
    assert report['rocks'] > 0 and report['craters'] > 0
    sources = report['dem_resolution']['loaded_at_origin']
    assert any(v['posting_m'] == 2 and v['centre_weight'] > .99 for v in sources)
    dem = addon.dem.TerrainDEM(LATITUDE, LONGITUDE)
    horizon = horizon_report(dem)
    assert horizon['sun_disc_above_sampled_horizon']
    surface_camera = bpy.data.objects['Lunar • surface camera']
    overview = bpy.data.objects.get('Moon Base • regional overview')
    if overview is None:
        overview = bpy.data.objects.new('Moon Base • regional overview', bpy.data.cameras.new('Connecting Ridge overview'))
        surface_camera.users_collection[0].objects.link(overview)
    overview.location = (10000, 10000, 12000)
    overview.rotation_euler = (Vector((0, -5500, -1000)) - overview.location).to_track_quat('-Z', 'Y').to_euler()
    overview.data.lens, overview.data.clip_end = 34, 150000
    overview['purpose'] = 'Oblique regional terrain context; not a landing trajectory or safe-site analysis'
    scene.camera = surface_camera
    scene['mission_context'] = json.dumps(CONTEXT, indent=2)
    scene['reference_study'] = 'NASA Moon Base / Blue Moon Mark 1 target REGION, anchored at NASA R01 reference point'
    anchor = bpy.data.objects['Lunar location • metadata']
    # Carry provenance through the existing Gazebo exporter without changing it.
    report['mission_context'] = CONTEXT
    report['sampled_solar_horizon'] = horizon
    anchor['generation_report'] = json.dumps(report, indent=2)
    p.stats = json.dumps(report)
    for filename in ('NASA_MOONBASE.md', 'lunar_terrain/data/PROVENANCE.md'):
        text = bpy.data.texts.get(Path(filename).name) or bpy.data.texts.new(Path(filename).name)
        text.clear()
        text.write((ROOT / filename).read_text())
    materials = [m for m in bpy.data.materials if m.get(addon.builder.OWNER) == p.last_owner
                 and m.node_tree and m.node_tree.nodes.get('HAPKE_CONTROLS')]
    assert len(materials) >= 2, 'Both rocks and soil must have Hapke materials'
    scene.render.threads_mode, scene.render.threads = 'FIXED', 8
    scene.render.resolution_x, scene.render.resolution_y = (960, 540) if args.draft else (1600, 900)
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 24 if args.draft else 64
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    (ROOT / 'examples/renders').mkdir(exist_ok=True)
    scene.render.filepath = '//renders/' + NAME + '.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    for camera, suffix in ((surface_camera, ''), (overview, '_Overview')):
        scene.camera = camera
        scene.render.filepath = '//renders/' + NAME + suffix + '.png'
        bpy.ops.render.render(write_still=True)
    scene.camera = surface_camera
    scene.render.filepath = '//renders/' + NAME + '.png'
    # Save the surface view as default and retain both editable cameras.
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    out = ROOT / 'build/moonbase'
    out.mkdir(parents=True, exist_ok=True)
    result = dict(passed=True, blender=bpy.app.version_string, draft=args.draft,
                  native_dem_grid_m=2, terrain_diameter_m=40000,
                  hapke_materials=len(materials), mission_context=CONTEXT,
                  generation=report, sampled_solar_horizon=horizon,
                  render_size=[scene.render.resolution_x, scene.render.resolution_y],
                  samples=scene.cycles.samples,
                  scope='Official Linux bpy 5.2.1 CPU Cycles; surface and overview rendered; GUI/GPU not tested')
    (out / (NAME + '_Blender_validation.json')).write_text(json.dumps(result, indent=2) + '\n')
    with blend.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    entry = dict(id='moonbase', title='NASA Moon Base / Connecting Ridge target-region study',
                 blend=blend.name, sha256=digest, bytes=blend.stat().st_size,
                 url=f'https://github.com/PastorD/lunar-terrain-blender/releases/download/{RELEASE}/{blend.name}',
                 archive=NAME + '_Gazebo.zip', model='lunar_moonbase')
    (out / 'catalog.json').write_text(json.dumps(dict(source_release=RELEASE, examples=[entry]), indent=2) + '\n')
    print('MOON BASE STUDY PASS', report['triangles'], 'triangles;', report['rocks'], 'rocks;', digest, flush=True)


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
