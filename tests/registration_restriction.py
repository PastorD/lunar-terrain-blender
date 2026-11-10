"""Regression for the 1.3.0 _RestrictData.scenes installation failure."""
from pathlib import Path
import sys,os,json,tomllib
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import bpy,_bpy_restrict_state as restrict

def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    aliases_differ=restrict._bpy is not bpy
    with patch.object(restrict,'_bpy',bpy):
        # Include import-time code in the restricted startup check.
        with restrict.RestrictBlend():
            import lunar_terrain as addon
            assert addon.bpy is bpy
            assert isinstance(addon.bpy.data,restrict._RestrictData)
            assert isinstance(addon.bpy.context,restrict._RestrictContext)
            addon.register()
        assert hasattr(bpy.types.Scene,'lunar_terrain')
        scene=bpy.context.scene;assert scene.lunar_terrain.busy is False
        scene.lunar_terrain.latitude=20.1908
        with restrict.RestrictBlend():addon.unregister()
        assert not hasattr(bpy.types.Scene,'lunar_terrain')
        with restrict.RestrictBlend():addon.register()
        assert scene.lunar_terrain.busy is False
        assert abs(scene.lunar_terrain.latitude-20.1908)<1e-5
        with restrict.RestrictBlend():addon.unregister()
    manifest=tomllib.loads((ROOT/'lunar_terrain/blender_manifest.toml').read_text())
    result=dict(passed=True,blender=bpy.app.version_string,addon_version=manifest['version'],wheel_module_alias_bridged=aliases_differ,restricted_data_type='_RestrictData',restricted_context_type='_RestrictContext',restricted_import_register_unregister=True,disable_reenable=True,default_busy_false=True,scene_setting_retained=True,scope='Official Linux bpy 5.2.1 with Blender restriction manager applied to the addon bpy module; not a GUI session')
    (ROOT/'tests/registration_results.json').write_text(json.dumps(result,indent=2));print('REGISTRATION PASS',result,flush=True)

if __name__=='__main__':
    code=0
    try:run()
    except Exception:
        import traceback;traceback.print_exc();code=1
    sys.stdout.flush();sys.stderr.flush();os._exit(code)
