"""Install the actual ZIP through Blender's extension operator in an isolated profile.

Usage: blender -b --python tests/install_extension.py -- /absolute/addon.zip
or: python tests/install_extension.py /absolute/addon.zip (official bpy module).
"""
from pathlib import Path
import os, sys, tempfile, json, importlib, platform, tomllib, hashlib, argparse
ROOT=Path(__file__).resolve().parents[1]
profile=tempfile.TemporaryDirectory(prefix='lunar-extension-test-')
os.environ['BLENDER_USER_RESOURCES']=profile.name
import bpy, addon_utils, numpy as np
import _bpy_restrict_state as restrict
from unittest.mock import patch

def run():
    assert bpy.app.version[:2]==(5,2), bpy.app.version_string
    parser=argparse.ArgumentParser()
    parser.add_argument('archive',type=Path)
    parser.add_argument('--upgrade-from',type=Path)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    args=parser.parse_args(argv)
    archive=args.archive.resolve();assert archive.is_file()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.system.use_online_access=False
    directory=Path(profile.name)/'repository';directory.mkdir()
    assert bpy.ops.preferences.extension_repo_add(name='Lunar Compatibility Test',type='LOCAL',
        use_custom_directory=True,custom_directory=str(directory))=={'FINISHED'}
    repo=next(r for r in bpy.context.preferences.extensions.repos if Path(r.directory)==directory)
    name=f'bl_ext.{repo.module}.lunar_terrain'
    upgrade=None; prior_class_count=0
    if args.upgrade_from:
        prior=args.upgrade_from.resolve();assert prior.is_file()
        assert bpy.ops.extensions.package_install_files(filepath=str(prior),repo=repo.module,
            enable_on_install=True)=={'FINISHED'}
        previous=importlib.import_module(name)
        prior_class_count=len(previous.CLASSES)
        previous_manifest=tomllib.loads((Path(previous.__file__).parent/'blender_manifest.toml').read_text())
        bpy.context.scene.lunar_terrain.latitude=-88.9
        bpy.context.scene.lunar_terrain.seed=420318
        bpy.context.scene.lunar_terrain.site='BLUEGHOST'
        bpy.context.scene.lunar_terrain.appearance='BLUEGHOST'
        prior_cache=Path(previous.cache_path())
        marker=prior_cache/'upgrade_check.txt';marker.write_text('Retain downloaded DEM cache')
        upgrade=dict(from_version=previous_manifest['version'],from_sha256=hashlib.sha256(prior.read_bytes()).hexdigest())
    assert bpy.ops.extensions.package_install_files(filepath=str(archive),repo=repo.module,
        enable_on_install=True)=={'FINISHED'}
    addon=importlib.import_module(name)
    assert addon_utils.check(name)==(True,True)
    assert addon.bpy is bpy, 'Test must restrict the bpy module used by the installed extension'
    manifest=tomllib.loads((Path(addon.__file__).parent/'blender_manifest.toml').read_text())
    assert manifest['version']==tomllib.loads((ROOT/'lunar_terrain/blender_manifest.toml').read_text())['version'] and manifest['blender_version_min']=='5.2.0'
    assert hasattr(bpy.types,'LUNAR_PT_main') and hasattr(bpy.types.Scene,'lunar_terrain')
    cache=Path(addon.cache_path());assert cache.is_dir()
    assert cache.is_relative_to(Path(profile.name))
    assert not cache.is_relative_to(Path(addon.__file__).parent)
    if upgrade:
        assert abs(bpy.context.scene.lunar_terrain.latitude+88.9)<1e-4
        assert bpy.context.scene.lunar_terrain.seed==420318
        assert bpy.context.scene.lunar_terrain.site=='BLUEGHOST'
        assert bpy.context.scene.lunar_terrain.appearance=='BLUEGHOST'
        assert bpy.context.scene.lunar_terrain.regolith_relief==1
        assert cache==prior_cache and marker.read_text()=='Retain downloaded DEM cache'
        assert not bpy.context.scene.lunar_terrain.busy
        upgrade.update(settings_retained=True,cache_retained=True,idle=True)
    rows=[]
    for site in ('APOLLO17','SOUTH','CE6','BLUEGHOST','MOONBASE','VIPER','NOBILE2','MALAPERT','CH3'):
        s=bpy.context.scene;p=s.lunar_terrain;p.site=site
        assert bpy.ops.lunar.apply_preset()=={'FINISHED'}
        p.download_first=False;p.outer_radius=100;p.detail_radius=10;p.mesh_spacing=.5
        p.rock_coverage=0;p.micro_density=0;p.crater_density=0;p.micro_craters=0
        p.include_outpost=(site=='APOLLO17')
        assert bpy.ops.lunar.build()=={'FINISHED'}
        report=json.loads(p.stats)
        expected={'APOLLO17':2.,'CE6':4.,'SOUTH':2.,'BLUEGHOST':3.,'CH3':3.,'MOONBASE':2.,'VIPER':5.,'NOBILE2':5.,'MALAPERT':4.}[site]
        assert abs(min(v['posting_m'] for v in report['dem_resolution']['loaded_at_origin'])-expected)<1e-8
        local=addon.dem.TerrainDEM(p.latitude,p.longitude,cache)
        assert np.isfinite(local.height(np.linspace(-20000,20000,400),np.zeros(400))).all()
        assert (Path(addon.__file__).parent/'data/Lunar_DEM_Map.html').is_file()
        assert (Path(addon.__file__).parent/'data/Chandrayaan3_References.html').is_file()
        assert report['triangles']>1000 and s.camera and s.world
        rows.append(dict(site=site,triangles=report['triangles'],origin_elevation_m=report['origin_elevation_m'],
                         outpost=p.include_outpost,native_grid_m=expected,finite_40km_transect=True,passed=True))
    assert (Path(addon.__file__).parent/'data/Lunar_Atlas.html').is_file()
    location=Path(profile.name)/'atlas-location.json'
    for site in ('VIPER','MALAPERT','CH3'):
        location.write_text(json.dumps(dict(schema='lunar-terrain-location-v1',preset=site)))
        assert bpy.ops.lunar.import_location(filepath=str(location))=={'FINISHED'}
        assert bpy.context.scene.lunar_terrain.site==site
    for value in ({'schema':'wrong','preset':'VIPER'},{'schema':'lunar-terrain-location-v1','preset':'../../evil'},['VIPER']):
        location.write_text(json.dumps(value))
        try:
            result=bpy.ops.lunar.import_location(filepath=str(location));assert result=={'CANCELLED'}
        except RuntimeError as error:
            assert 'location' in str(error).lower() or 'preset' in str(error).lower()
        assert bpy.context.scene.lunar_terrain.site=='CH3'
    assert bpy.ops.lunar.update_rocks()=={'FINISHED'}
    assert bpy.ops.lunar.clear()=={'FINISHED'}
    addon_utils.disable(name,default_set=True)
    assert not hasattr(bpy.types.Scene,'lunar_terrain')
    addon_utils.enable(name,default_set=True)
    assert addon_utils.check(name)==(True,True)
    assert bpy.context.scene.lunar_terrain.site=='CH3'
    assert bpy.context.scene.lunar_terrain.appearance=='CH3'
    result=dict(blender=bpy.app.version_string,python=platform.python_version(),numpy=np.__version__,
                archive=archive.name,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                addon_version=manifest['version'],minimum_blender=manifest['blender_version_min'],
                installed_via='bpy.ops.extensions.package_install_files',extension_namespace=name,
                panel_registered=True,extension_cache=True,disable_reenable=True,sites=rows,passed=True,
                restricted_registration_calls=len(RESTRICTED_CLASSES),
                restricted_data_type='_RestrictData',restricted_context_type='_RestrictContext',
                wheel_module_alias_bridged=WHEEL_ALIAS_DIFFERS,
                online_access=False,upgrade=upgrade,atlas_import=True,rejected_unknown_location=True,
                scope='Linux, official bpy module, headless CPU; no interactive UI or GPU validation')
    assert len(RESTRICTED_CLASSES)==2*len(addon.CLASSES)+prior_class_count, 'Install, upgrade and re-enable must register under restriction'
    filename='install_upgrade_results.json' if upgrade else 'install_results.json'
    (ROOT/'tests'/filename).write_text(json.dumps(result,indent=2))
    print('EXTENSION INSTALLATION PASS',result,flush=True)
    addon_utils.disable(name,default_set=True)

RESTRICTED_CLASSES=[]
WHEEL_ALIAS_DIFFERS=restrict._bpy is not bpy
_original_register_class=bpy.utils.register_class

def checked_register_class(cls):
    if cls.__module__.startswith('bl_ext.') and '.lunar_terrain' in cls.__module__:
        assert isinstance(bpy.data,restrict._RestrictData), type(bpy.data)
        assert isinstance(bpy.context,restrict._RestrictContext), type(bpy.context)
        RESTRICTED_CLASSES.append(cls.__name__)
    return _original_register_class(cls)

if __name__=='__main__':
    try:
        # The wheel can retain a second bpy module in this helper. Point its
        # real restriction context manager at the module used by the add-on.
        with patch.object(restrict,'_bpy',bpy),patch.object(bpy.utils,'register_class',checked_register_class):
            run()
    except Exception:
        import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush()
        if not bpy.app.binary_path:os._exit(1)
        raise
    sys.stdout.flush();sys.stderr.flush()
    if not bpy.app.binary_path:os._exit(0)
