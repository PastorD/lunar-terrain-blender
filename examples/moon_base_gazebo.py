"""Export/package the generated Moon Base example with the shared Gazebo tools.

Run examples/moon_base.py first. Its catalogue pins the actual saved .blend.
No changes to the existing seven release scenes or their checksums are needed.
"""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('gazebo_examples', ROOT / 'gazebo/build_examples.py')
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'package'])
    parser.add_argument('--bpy-python', default=sys.executable)
    args = parser.parse_args()
    args.sources_dir = ROOT / 'examples'
    args.output_dir = ROOT / 'build/gazebo'
    args.dist = ROOT / 'dist/moonbase'
    catalog_path = ROOT / 'build/moonbase/catalog.json'
    EXPORT.CATALOG = json.loads(catalog_path.read_text())
    entry, = EXPORT.CATALOG['examples']
    assert entry['id'] == 'moonbase'
    folder = args.output_dir / entry['id']
    if args.command == 'build':
        EXPORT.build(entry, args)
        # The shared assembler's original seven scenes came from v1.5.0.
        # Substitute this example's actual release in its package README.
        readme = folder / 'README.md'
        readme.write_text(readme.read_text().replace('unchanged v1.5.0 geometry',
                         'saved ' + EXPORT.CATALOG['source_release'] + ' geometry')
                         + '\nSee NASA_MOONBASE.md for the target-region status, coordinate provenance and limitations.\n')
        shutil.copy2(ROOT / 'NASA_MOONBASE.md', folder / 'NASA_MOONBASE.md')
        manifest = json.loads((folder / 'export_manifest.json').read_text())
        assert manifest['source_sha256'] == entry['sha256']
        assert manifest['source_generation']['mission_context']['coordinate_role'].startswith('NASA Lunar Surface Data Book')
        print('MOON BASE EXPORT PASS', flush=True)
        return
    EXPORT.package(entry, args)
    stem = Path(entry['blend']).stem
    validation = ROOT / 'build/moonbase' / (stem + '_Blender_validation.json')
    result = json.loads(validation.read_text())
    assert result['passed'] and not result['draft'], 'Only full-quality, validated scenes may be released'
    assert EXPORT.checksum(args.sources_dir / entry['blend']) == entry['sha256']
    for path in (args.sources_dir / entry['blend'], validation, ROOT / 'NASA_MOONBASE.md',
                 args.sources_dir / 'renders' / (stem + '.png'),
                 args.sources_dir / 'renders' / (stem + '_Overview.png')):
        shutil.copy2(path, args.dist / path.name)
    shutil.copy2(catalog_path, args.dist / 'MoonBase_catalog.json')
    subprocess.run(['git', 'archive', '--format=zip', '--prefix=lunar-terrain-blender/',
                    '-o', str(args.dist / 'NASA_MoonBase_Source.zip'), 'HEAD'], cwd=ROOT, check=True)
    checks = [f'{EXPORT.checksum(path)}  {path.name}' for path in sorted(args.dist.iterdir())
              if path.is_file() and path.name != 'SHA256SUMS']
    (args.dist / 'SHA256SUMS').write_text('\n'.join(checks) + '\n')
    print('MOON BASE RELEASE PASS', len(checks), 'checksummed assets', flush=True)


if __name__ == '__main__':
    main()
