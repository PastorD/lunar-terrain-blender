"""Build/validate the extension with Blender's official CLI, or archive sources.

python tools/package_release.py --blender /path/to/blender --output-dir dist
python tools/package_release.py --complete --output-dir dist
python tools/package_release.py --source --output-dir dist

The official bpy wheel is supported for automated build validation. The
extension itself only needs Blender's bundled Python and NumPy.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / 'lunar_terrain'
DATA = EXTENSION / 'data'


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def official_cli(args):
    if args.extension_cli:
        return [sys.executable, str(Path(args.extension_cli).resolve())]
    if args.blender or shutil.which('blender'):
        return [args.blender or shutil.which('blender'), '--command', 'extension']
    spec = importlib.util.find_spec('bpy')
    if spec and spec.submodule_search_locations:
        candidates = sorted(Path(next(iter(spec.submodule_search_locations))).glob(
            '*/scripts/addons_core/bl_pkg/cli/blender_ext.py'))
        if len(candidates) == 1:
            return [sys.executable, str(candidates[0])]
    raise SystemExit('Use --blender /path/to/blender or run with the official bpy wheel installed')


def refresh_provenance(version):
    import numpy as np
    path = DATA / 'provenance.json'
    document = json.loads(path.read_text(encoding='utf-8'))
    document['prepared_for'] = f'Lunar Terrain {version}'
    document['data_packs'] = []
    for pack in sorted(DATA.glob('*.npz')):
        with np.load(pack, allow_pickle=False) as source:
            elevation = source['elevation']
            metadata = json.loads(str(source['metadata']))
        document['data_packs'].append(dict(
            file=pack.name, bytes=pack.stat().st_size, sha256=sha256(pack),
            shape=list(elevation.shape), dtype=str(elevation.dtype),
            elevation_array_sha256=hashlib.sha256(elevation.tobytes()).hexdigest(),
            metadata=metadata))
    catalog = DATA / 'dem_catalog.geojson'
    document['catalog'] = dict(file=catalog.name, sha256=sha256(catalog),
        features=len(json.loads(catalog.read_text(encoding='utf-8'))['features']))
    path.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')


def verify_zip(path, extension=False):
    with zipfile.ZipFile(path) as archive:
        if damaged := archive.testzip():
            raise RuntimeError(f'Damaged ZIP member: {damaged}')
        names = archive.namelist()
        if extension:
            assert 'blender_manifest.toml' in names and '__init__.py' in names
            assert not any('__pycache__' in n or n.endswith(('.pyc', '.partial', '.zip')) for n in names)
            for name in names:
                if name.endswith('.py'):
                    ast.parse(archive.read(name), filename=name)
    return len(names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--complete', action='store_true', help='Project, tests and example scenes')
    modes.add_argument('--source', action='store_true', help='Project and tests without example scenes')
    engine = parser.add_mutually_exclusive_group()
    engine.add_argument('--blender', help='Blender executable')
    engine.add_argument('--extension-cli', help='Official bl_pkg/cli/blender_ext.py')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == EXTENSION or EXTENSION in output.parents:
        parser.error('Output must be outside the installable lunar_terrain directory')
    output.mkdir(parents=True, exist_ok=True)
    manifest = tomllib.loads((EXTENSION / 'blender_manifest.toml').read_text(encoding='utf-8'))
    installer = not (args.complete or args.source)
    filename = (f"{manifest['id']}-{manifest['version']}.zip" if installer else
                'Lunar_Terrain_Complete.zip' if args.complete else 'Lunar_Terrain_DEM_Upgrade_Source.zip')
    target = output / filename
    with tempfile.TemporaryDirectory(prefix='.lunar-build-', dir=output) as temporary:
        staged = Path(temporary) / filename
        if installer:
            refresh_provenance(manifest['version'])
            command = official_cli(args)
            subprocess.run(command + ['validate', str(EXTENSION)], check=True)
            subprocess.run(command + ['build', '--source-dir', str(EXTENSION),
                                      '--output-filepath', str(staged)], check=True)
            subprocess.run(command + ['validate', str(staged)], check=True)
        else:
            with zipfile.ZipFile(staged, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(ROOT.rglob('*')):
                    relative = path.relative_to(ROOT)
                    if not path.is_file() or output == path or output in path.parents:
                        continue
                    if any(p in ('__pycache__', 'catalog_source', '.git', 'dist') for p in relative.parts):
                        continue
                    if path.suffix in ('.pyc', '.pyo', '.partial', '.zip', '.blend1', '.blend2'):
                        continue
                    if args.source and relative.parts[0] == 'examples':
                        continue
                    member = Path(ROOT.name) / relative if args.complete else relative
                    archive.write(path, member)
        with staged.open('rb') as stream:
            os.fsync(stream.fileno())
        count = verify_zip(staged, extension=installer)
        os.replace(staged, target)
    result = dict(archive=target.name, bytes=target.stat().st_size,
                  sha256=sha256(target), files=count, version=manifest['version'],
                  official_build_and_validation=installer, zip_integrity=True,
                  python_syntax_checked=installer)
    if installer:
        (ROOT / 'tests/extension_package_results.json').write_text(
            json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
