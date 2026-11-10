"""Refresh embedded release documentation; do not rebuild or retune scenes."""
from pathlib import Path
import bpy,sys,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import lunar_terrain as addon

def run():
    addon.register()
    for name in ('Apollo17_Surface','Apollo17_Outpost','ChangE6_Surface','Rock_Detail'):
        file=ROOT/'examples'/(name+'.blend')
        bpy.ops.wm.open_mainfile(filepath=str(file))
        for doc in ('README.md','APPEARANCE_UPDATE.md','BLENDER_52_UPDATE.md','VALIDATION.md'):
            key='START_HERE.md' if doc=='README.md' else doc
            t=bpy.data.texts.get(key) or bpy.data.texts.new(key);t.clear();t.write((ROOT/doc).read_text())
        bpy.ops.wm.save_as_mainfile(filepath=str(file),compress=True)
        print('Updated embedded documents:',name,flush=True)

if __name__=='__main__':
    try:run()
    except Exception:
        import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush()
        if not bpy.app.binary_path:os._exit(1)
        raise
    sys.stdout.flush();sys.stderr.flush()
    if not bpy.app.binary_path:os._exit(0)
