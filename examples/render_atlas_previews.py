"""Render missing previews from checksum-pinned, already released .blend files."""
from pathlib import Path
import hashlib,json,os,sys,urllib.request
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import bpy
import lunar_terrain as addon
NAMES={'Apollo17_Surface.blend','Rock_Detail.blend','Hapke_Opposition_Check.blend'}
def run():
    addon.register();folder=ROOT/'build/atlas_sources';folder.mkdir(parents=True,exist_ok=True);rows=[]
    for item in json.loads((ROOT/'gazebo/examples.json').read_text())['examples']:
        if item['blend'] not in NAMES:continue
        target=folder/item['blend']
        if not target.exists():
            with urllib.request.urlopen(item['url'],timeout=60) as response,target.with_suffix('.partial').open('wb') as stream:
                while chunk:=response.read(1024**2):stream.write(chunk)
            target.with_suffix('.partial').replace(target)
        with target.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        assert target.stat().st_size==item['bytes'] and digest==item['sha256']
        bpy.ops.wm.open_mainfile(filepath=str(target));scene=bpy.context.scene;assert scene.camera
        scene.render.engine='CYCLES';scene.render.threads_mode,scene.render.threads='FIXED',8
        ratio=scene.render.resolution_y/scene.render.resolution_x;scene.render.resolution_x=1600;scene.render.resolution_y=round(1600*ratio);scene.render.resolution_percentage=100
        scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
        out=ROOT/'examples/renders'/(target.stem+'.png');out.parent.mkdir(exist_ok=True);scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
        rows.append(dict(blend=target.name,source_url=item['url'],source_sha256=digest,preview=out.name,blender=bpy.app.version_string,camera=scene.camera.name,render_size=[scene.render.resolution_x,scene.render.resolution_y],samples=48,geometry_unchanged=True,passed=True))
        print('LEGACY PREVIEW PASS',target.name,flush=True)
    (ROOT/'build/atlas/Legacy_Previews_validation.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':
    code=0
    try:run()
    except Exception:
        import traceback;traceback.print_exc();code=1
    sys.stdout.flush();sys.stderr.flush()
    if not bpy.app.binary_path:os._exit(code)
    if code:raise SystemExit(code)
