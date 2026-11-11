#!/usr/bin/env python3
"""Build or package any checked example. Downloads are pinned by SHA-256."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CATALOG=json.loads((ROOT/'examples.json').read_text())


def checksum(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def source_file(entry,folder):
    folder.mkdir(parents=True,exist_ok=True);target=folder/entry['blend']
    if not target.exists():
        request=urllib.request.Request(entry['url'],headers={'User-Agent':'LunarTerrain-Gazebo/1.0'})
        with tempfile.NamedTemporaryFile(dir=folder,delete=False) as stream:
            temporary=Path(stream.name)
            try:
                with urllib.request.urlopen(request,timeout=180) as response:shutil.copyfileobj(response,stream)
                stream.flush()
                if temporary.stat().st_size!=entry['bytes'] or checksum(temporary)!=entry['sha256']:
                    raise ValueError(f"Download checksum mismatch: {entry['blend']}")
                os.replace(temporary,target)
            finally:temporary.unlink(missing_ok=True)
    if target.stat().st_size!=entry['bytes'] or checksum(target)!=entry['sha256']:
        raise ValueError(f"Source differs from v1.5.0: {target}. Use a separate folder for custom scenes.")
    return target


def build(entry,args):
    source=source_file(entry,args.sources_dir.resolve())
    package=args.output_dir.resolve()/entry['id']
    subprocess.run([args.bpy_python,str(ROOT/'scripts/export_blender.py'),str(source),str(package),
                    '--model-id',entry['model'],'--title',entry['title']],check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/make_worlds.py'),str(package)],check=True)
    for name in ['run.sh','test_server.sh']:
        shutil.copy2(ROOT/name,package/name);(package/name).chmod(0o755)
    for name in ['run_offline_tests.sh','render_export.cc','physics_export.cc','resolve_world.py']:
        shutil.copy2(ROOT/'tests'/name,package/'tests'/name)
    (package/'tests/run_offline_tests.sh').chmod(0o755)
    shutil.copy2(ROOT.parent/'LICENSE',package/'LICENSE')
    shutil.copy2(ROOT/'README.md',package/'EXPORT_GUIDE.md')
    provenance=ROOT.parent/'lunar_terrain/data/PROVENANCE.md'
    if provenance.exists():shutil.copy2(provenance,package/'DATA_PROVENANCE.md')
    d=json.loads((package/'export_manifest.json').read_text())
    d.update(example_id=entry['id'],source_release=CATALOG['source_release'],
             exporter_commit=os.environ.get('GITHUB_SHA','local checkout'))
    (package/'export_manifest.json').write_text(json.dumps(d,indent=2)+'\n')
    radius=d['terrain_collision']['coverage_radius_m'] if d['terrain_collision'] else None
    extent=f'{2*radius:g} m diameter; source lunar curvature retained' if radius else 'Two flat diagnostic panels; no DEM terrain'
    (package/'README.md').write_text(f'''# {entry['title']} — Gazebo Harmonic

Extract this whole folder and run `bash run.sh`. Blender is not required.
For a headless server: `bash run.sh -s --headless-rendering`.

- World: `worlds/{entry['id']}.sdf`
- Model: `model://{entry['model']}`
- Camera topic: `/{entry['id']}/camera/image`
- Extent: {extent}
- Source: [{entry['blend']}]({entry['url']}) (unchanged v1.5.0 geometry)
- Rock instances: {d['rock_instance_count']:,}; additional objects: {len(d['extra_objects']):,}
- Gravity: 1.62 m/s²; static terrain/rock/hardware collisions.

**Stock Ogre2 PBR materials do not retain Hapke opposition or backscatter.**
The diagnostic export deliberately has identical PBR panels. Use its original
.blend to inspect the opposition effect. See EXPORT_GUIDE.md for limitations,
rebuilding and tests, and export_manifest.json for exact source settings and DEMs.

`bash tests/run_offline_tests.sh` checks actual Ogre2 rendering and DART physics.
`bash test_server.sh` checks the full Gazebo server and camera output.
When built by CI, TEST_REPORT.md and test_output/ contain the results.
''')
    print('BUILT',package,flush=True)


def package(entry,args):
    folder=args.output_dir.resolve()/entry['id'];evidence=folder/'test_output'
    server=json.loads((evidence/'server_result.json').read_text())
    physics=(evidence/'physics.log').read_text();render=(evidence/'render.log').read_text()
    if not server['passed'] or 'PHYSICS PASS' not in physics or 'RENDER PASS' not in render:
        raise RuntimeError('Required Gazebo checks did not pass; will not publish a passing report')
    run_url=''
    if os.environ.get('GITHUB_RUN_ID'):
        run_url=f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    d=json.loads((folder/'export_manifest.json').read_text())
    report=dict(example=entry['id'],source_sha256=d['source_sha256'],
                exporter_commit=d['exporter_commit'],workflow_url=run_url,
                blender=d['exporter_blender'],server=server,physics='PASS',render='PASS',
                gui='Not tested',ros_bridge='Not tested',photometry='PBR approximation; Hapke not implemented')
    (evidence/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (folder/'TEST_REPORT.md').write_text(f'''# {entry['title']} — validation

Source SHA-256: `{d['source_sha256']}`.
Exporter commit: `{d['exporter_commit']}`. Blender: {d['exporter_blender']}.
Workflow: {run_url or 'Local run'}.

| Check | Result |
|---|---|
| Gazebo Common visual mesh loading and Ogre2 rendered frame | PASS |
| DART mesh collisions, five falling boxes settling at 5 s | PASS |
| Lunar free fall (1.62 m/s² at 1 s) and final contacts | PASS |
| Full gz sim server / camera smoke test | PASS: {server['frames']} frames |
| Interactive GUI / ROS bridge | Not tested |
| Photometric equivalence to Blender Hapke | Not implemented |

See test_output/ for the actual preview, CSV trajectories and complete logs.
Terrain height comparisons in export_manifest.json are sampled approximations,
not global error bounds or DEM accuracy estimates. The exported hardware is
static geometry, with no rover joints, controllers or deformable soil.
''')
    args.dist.mkdir(parents=True,exist_ok=True)
    archive=args.dist/entry['archive']
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for path in sorted(folder.rglob('*')):
            if not path.is_file():continue
            rel=path.relative_to(folder)
            if '__pycache__' in rel.parts or 'frames' in rel.parts:continue
            if rel.parts[0]=='test_output' and path.suffix not in {'.png','.log','.json','.csv'}:continue
            bundle.write(path,Path(entry['id'])/rel)
    for suffix,source in [('_Gazebo.png',evidence/'preview.png'),('_Gazebo_validation.json',evidence/'validation.json')]:
        shutil.copy2(source,args.dist/(Path(entry['blend']).stem+suffix))
    print('PACKAGED',archive,checksum(archive),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['build','package','list'])
    p.add_argument('--example',default='all',choices=['all']+[e['id'] for e in CATALOG['examples']])
    p.add_argument('--sources-dir',type=Path,default=ROOT.parent/'examples')
    p.add_argument('--output-dir',type=Path,default=ROOT.parent/'build/gazebo')
    p.add_argument('--dist',type=Path,default=ROOT.parent/'dist/gazebo')
    p.add_argument('--bpy-python',default=sys.executable,help='Python 3.13 with official bpy 5.2.1 installed')
    args=p.parse_args()
    for entry in CATALOG['examples']:
        if args.example!='all' and entry['id']!=args.example:continue
        if args.command=='list':print(entry['id'],entry['blend'])
        else:globals()[args.command](entry,args)

if __name__=='__main__':main()
