"""Roughness angle sweep and look-control regression. Blender 5.2 background Python."""
import bpy,sys,os,math,json,tempfile
from pathlib import Path
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import lunar_terrain as addon
from lunar_terrain import hapke,builder,appearance

def phase(i,e,psi):
 i,e,psi=map(math.radians,(i,e,psi))
 return math.degrees(math.acos(np.clip(math.cos(i)*math.cos(e)+math.sin(i)*math.sin(e)*math.cos(psi),-1,1)))

def smooth_reference(a,i,e,p):
 u0,u=math.cos(math.radians(i)),math.cos(math.radians(e));a=math.radians(a)
 b,c,w=p['b'],p['c'],p['w'];t=math.tan(a/2)
 P=(1+c)/2*(1-b*b)/(1-2*b*math.cos(a)+b*b)**1.5+(1-c)/2*(1-b*b)/(1+2*b*math.cos(a)+b*b)**1.5
 r=(1-math.sqrt(1-w))/(1+math.sqrt(1-w))
 H=lambda x:1/(1-w*x*(r+(1-2*r*x)/2*math.log1p(1/x)))
 return w/(4*math.pi*(u0+u))*((1+p['B_SH0']/(1+t/p['h_SH']))*P+H(u0)*H(u)-1)

def run():
 result={'blender':bpy.app.version_string,'version':'.'.join(map(str,addon.bl_info['version']))};rec=sm=0.;count=0
 for i in (0,15,50,75,85,89.9):
  for e in (0,15,50,75,85,89.9):
   for psi in (0,15,90,165,180):
    a=phase(i,e,psi);f=hapke.analytic(a,i,e);g=hapke.analytic(a,e,i)
    assert math.isfinite(f) and f>=0
    rec=max(rec,abs(f-g)/max(f,g,1e-12))
    ref=smooth_reference(a,i,e,hapke.DEFAULTS);sm=max(sm,abs(hapke.analytic(a,i,e,theta=0)-ref)/max(ref,1e-12));count+=1
 assert rec<1e-8 and sm<1e-5
 assert hapke.analytic(90,100,30)==0 and hapke.analytic(90,30,100)==0
 assert abs(hapke.analytic(0,B_CB0=.3)/hapke.analytic(0)-1.3)<1e-10
 result['numeric']={'cases':count,'reciprocity_error':rec,'zero_roughness_closed_form_error':sm,'finite_nonnegative':True,'unlit_zero':True,'optional_CBOE_zero_phase_limit':True}

 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'examples/Hapke_Opposition_Check.blend'))
 s=bpy.context.scene;sun=bpy.data.objects['Diagnostic Sun'];cam=s.camera
 s.render.resolution_x=256;s.render.resolution_y=144;s.cycles.samples=16
 rows=[]
 with tempfile.TemporaryDirectory() as temp:
  for i,e,psi in [(0,0,0),(0,60,90),(30,60,45),(60,30,45),(72,80,0),(80,72,0),(88,60,135),(60,80,180)]:
   ir,er,pr=map(math.radians,(i,e,psi))
   sun.rotation_euler=Vector((math.sin(ir)*math.sin(pr),-math.sin(ir)*math.cos(pr),math.cos(ir))).to_track_quat('Z','Y').to_euler()
   cam.location=(0,-20*math.sin(er),20*math.cos(er));cam.rotation_euler=(er,0,0);bpy.context.view_layer.update()
   s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_depth='32';s.render.filepath=str(Path(temp)/'test.exr')
   bpy.ops.render.render(write_still=True)
   im=bpy.data.images.load(s.render.filepath,check_existing=False);a=np.array(im.pixels[:]).reshape(144,256,4)
   measured=float(a[66:78,58:70,:3].mean());bpy.data.images.remove(im)
   alpha=phase(i,e,psi);expected=hapke.analytic(alpha,i,e)*math.cos(ir)
   err=abs(measured-expected)/expected
   row=dict(incidence=i,emergence=e,relative_azimuth=psi,phase=alpha,rendered=measured,expected=expected,relative_error=err)
   rows.append(row);assert err<.005,row
 result['render_angles']=rows;result['max_radiance_relative_error']=max(r['relative_error'] for r in rows)

 bpy.ops.wm.read_factory_settings(use_empty=True);addon.register();s=bpy.context.scene;p=s.lunar_terrain
 p.outer_radius=100;p.detail_radius=10;p.mesh_spacing=.5;p.rock_coverage=0;p.micro_density=0;p.crater_density=0;p.micro_craters=0
 assert bpy.ops.lunar.build()=={'FINISHED'}
 owner=p.last_owner;camera=s.camera;geo={o.name:o.data.as_pointer() for o in s.objects if o.type=='MESH'}
 sun=next(o for o in s.objects if o.type=='LIGHT');sun.rotation_euler=(.2,.4,.6);sun.data.energy=2.3;bpy.context.view_layer.update();rot=tuple(sun.rotation_euler)
 p.appearance='CHANGE';bpy.ops.lunar.apply_appearance()
 assert owner==p.last_owner and camera==s.camera and geo=={o.name:o.data.as_pointer() for o in s.objects if o.type=='MESH'}
 assert tuple(sun.rotation_euler)==rot and abs(sun.data.energy-2.3)<1e-6
 expected=appearance.parameters_at(-41.6385,206.0148)
 assert abs(p.single_scattering_albedo-expected['w'])<1e-6
 try:appearance.set_photometry(p,-89,0)
 except ValueError:pass
 else:raise AssertionError('Must not extrapolate missing polar data')
 p.latitude=20.1908;p.longitude=30.7717;s.view_settings.exposure=.75;bpy.ops.lunar.load_photometry()
 assert abs(p.single_scattering_albedo-hapke.DEFAULTS['w'])<1e-6 and s.view_settings.exposure==.75
 result['controls']={'preserves_geometry_camera_manual_sun_rotation_energy':True,'atlas_lookup':True,'polar_missing_coverage_retained':True,'location_lookup_preserves_exposure':True}
 result['passed']=True
 result['limits']='Implementation tests, not laboratory validation of the regional parameters or calibrated inversion of reference photographs.'
 (ROOT/'tests/roughness_results.json').write_text(json.dumps(result,indent=2));print('ROUGHNESS AND CONTROLS PASS',result['max_radiance_relative_error'],flush=True)

if __name__=='__main__':
 try:run()
 except Exception:
  import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush()
  if not bpy.app.binary_path:os._exit(1)
  raise
 sys.stdout.flush();sys.stderr.flush()
 if not bpy.app.binary_path:os._exit(0)
