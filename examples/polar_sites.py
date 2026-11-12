"""Build three polar terrain examples: python examples/polar_sites.py [--draft]."""
from pathlib import Path
import argparse,json,math,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
import lunar_terrain as addon
NAMES={'VIPER':'VIPER_Mons_Mouton','NOBILE2':'Nobile_Rim_2','MALAPERT':'Malapert_Massif'}
def run():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--site',choices=NAMES);parser.add_argument('--draft',action='store_true');parser.add_argument('--probe',action='store_true')
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ([] if bpy.app.binary_path else sys.argv[1:]);args=parser.parse_args(argv);addon.register()
    for key in ([args.site] if args.site else NAMES):
        spec=addon.sites.POLAR_SITES[key];terrain=addon.dem.TerrainDEM(spec['latitude'],spec['longitude'])
        distances=np.unique(np.r_[np.arange(2.,102.,2.),np.geomspace(100,20000,400)]);az=math.radians(spec['sun_azimuth'])
        angles=np.degrees(np.arctan2(terrain.height(np.sin(az)*distances,np.cos(az)*distances)-1.8,distances))
        horizon=dict(azimuth_deg=spec['sun_azimuth'],elevation_deg=float(max(angles)),sun_elevation_deg=spec['sun_elevation'],disc_above_sampled_horizon=bool(max(angles)<spec['sun_elevation']-.265),scope='DEM-only radial profile at 1.8 m within 20 km; not an illumination forecast')
        print(key,'HORIZON',json.dumps(horizon),flush=True)
        if args.probe:continue
        bpy.ops.wm.read_factory_settings(use_empty=True);p=bpy.context.scene.lunar_terrain;p.site=key
        assert bpy.ops.lunar.apply_preset()=={'FINISHED'}
        p.download_first=False;p.outer_radius,p.detail_radius,p.mesh_spacing=20000,24,.12;p.focus_mode,p.curvature='LOCATION',True;p.seed=20261111+list(NAMES).index(key);p.include_outpost=False
        assert bpy.ops.lunar.build()=={'FINISHED'}
        scene=bpy.context.scene;report=json.loads(p.stats);actual=min(r['posting_m'] for r in report['dem_resolution']['loaded_at_origin'])
        assert actual==spec['grid_m'],(key,actual)
        assert report['rocks']>0 and report['craters']>0 and p.curvature
        context=dict(spec,checked=addon.sites.CHECKED,photometry='Apollo 17 regional Hapke analogue, not a polar fit',lighting='Illustrative manual Sun, not dated ephemeris',geometry='Real DEM plus synthetic sub-resolution rocks, craterlets and regolith',hardware='Terrain study only; no official rover, lander or base architecture')
        report['mission_context']=context;report['sampled_solar_horizon']=horizon;p.stats=json.dumps(report)
        bpy.data.objects['Lunar location • metadata']['generation_report']=json.dumps(report,indent=2);scene['mission_context']=json.dumps(context,indent=2)
        text=bpy.data.texts.new('POLAR_SITES.md');text.write((ROOT/'POLAR_SITES.md').read_text())
        count=sum(1 for m in bpy.data.materials if m.get(addon.builder.OWNER)==p.last_owner and m.node_tree and m.node_tree.nodes.get('HAPKE_CONTROLS'));assert count>=2
        scene.render.threads_mode,scene.render.threads='FIXED',8
        scene.render.resolution_x,scene.render.resolution_y=(960,540) if args.draft else (1600,900)
        scene.render.resolution_percentage=100;scene.cycles.samples=24 if args.draft else 64;scene.cycles.use_denoising=True
        scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
        (ROOT/'examples/renders').mkdir(exist_ok=True);name=NAMES[key];scene.render.filepath='//renders/'+name+'.png';path=ROOT/'examples'/(name+'.blend')
        bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True);bpy.ops.render.render(write_still=True)
        bpy.ops.wm.open_mainfile(filepath=str(path));scene=bpy.context.scene
        assert scene.camera and json.loads(scene.lunar_terrain.stats)['mission_context']['name']==spec['name']
        result=dict(passed=True,blender=bpy.app.version_string,draft=args.draft,native_dem_grid_m=actual,terrain_diameter_m=40000,hapke_materials=count,generation=report,sampled_solar_horizon=horizon,reopened_saved_scene=True,render_size=[scene.render.resolution_x,scene.render.resolution_y],samples=scene.cycles.samples,scope='Official Linux bpy 5.2.1 CPU Cycles; GUI/GPU and Gazebo not tested for this example')
        out=ROOT/'build/polar_examples';out.mkdir(parents=True,exist_ok=True);(out/(name+'_validation.json')).write_text(json.dumps(result,indent=2)+'\n')
        print('POLAR EXAMPLE PASS',key,report['triangles'],'triangles',flush=True)
if __name__=='__main__':
    code=0
    try:run()
    except Exception:
        import traceback;traceback.print_exc();code=1
    sys.stdout.flush();sys.stderr.flush()
    if not bpy.app.binary_path:os._exit(code)
    if code:raise SystemExit(code)
