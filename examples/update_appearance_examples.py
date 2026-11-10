"""Upgrade saved Apollo examples and build Chang'e-6. Optional argument APOLLO or CHANGE."""
import bpy,sys,os,json,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import lunar_terrain as addon

def finish(name,width,height):
 s=bpy.context.scene;s['lunar_material_version']=tomllib.loads((ROOT/'lunar_terrain/blender_manifest.toml').read_text())['version']
 for filename in ('README.md','APPEARANCE_UPDATE.md'):
  key='START_HERE.md' if filename=='README.md' else filename
  t=bpy.data.texts.get(key) or bpy.data.texts.new(key);t.clear();t.write((ROOT/filename).read_text())
 s.render.threads_mode='FIXED';s.render.threads=8;s.render.resolution_x=width;s.render.resolution_y=height;s.render.resolution_percentage=100
 s.cycles.samples=48;s.cycles.use_denoising=True
 s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='8'
 s.render.filepath='//renders/'+name+'.png'
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'examples'/(name+'.blend')),compress=True)
 bpy.ops.render.render(write_still=True)
 print('RENDER COMPLETE',name,'exposure',s.view_settings.exposure,flush=True)

def run():
 addon.register();which=sys.argv[-1] if sys.argv[-1] in {'APOLLO','CHANGE'} else 'ALL'
 if which in {'ALL','APOLLO'}:
  for name,w,h in [('Apollo17_Surface',1100,1100),('Apollo17_Outpost',1800,1100)]:
   bpy.ops.wm.open_mainfile(filepath=str(ROOT/'examples'/(name+'.blend')))
   s=bpy.context.scene;p=s.lunar_terrain;camera=s.camera
   geometry={o.name:o.data.as_pointer() for o in s.objects if o.type=='MESH'}
   p.appearance='APOLLO';assert bpy.ops.lunar.apply_appearance()=={'FINISHED'}
   assert camera==s.camera and geometry=={o.name:o.data.as_pointer() for o in s.objects if o.type=='MESH'}
   finish(name,w,h)
 if which in {'ALL','CHANGE'}:
  bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;p=s.lunar_terrain
  p.site='CE6';bpy.ops.lunar.apply_preset();p.outer_radius=10000
  assert bpy.ops.lunar.build()=={'FINISHED'}
  finish('ChangE6_Surface',1280,960)
  (ROOT/'examples/ChangE6_generation_report.json').write_text(p.stats)

if __name__=='__main__':
 try:run()
 except Exception:
  import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush()
  if not bpy.app.binary_path:os._exit(1)
  raise
 sys.stdout.flush();sys.stderr.flush()
 if not bpy.app.binary_path:os._exit(0)
