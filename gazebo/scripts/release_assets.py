"""Require all seven tested examples, bundle source and write release checksums."""
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];dist=Path(sys.argv[1])
catalog=json.loads((root/'examples.json').read_text())
for e in catalog['examples']:
    assert (dist/e['archive']).is_file(),f"Missing {e['archive']}"
    report=json.loads((dist/(Path(e['blend']).stem+'_Gazebo_validation.json')).read_text())
    assert report['source_sha256']==e['sha256']
    assert report['physics']==report['render']=='PASS' and report['server']['passed']
with zipfile.ZipFile(dist/'Lunar_Terrain_Gazebo_Exporter.zip','w',zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(root.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or 'test_output' in path.parts:continue
        bundle.write(path,Path('lunar-terrain-gazebo/gazebo')/path.relative_to(root))
    bundle.write(root.parent/'LICENSE','lunar-terrain-gazebo/LICENSE')
    bundle.write(root.parent/'lunar_terrain/data/PROVENANCE.md','lunar-terrain-gazebo/lunar_terrain/data/PROVENANCE.md')
lines=[]
for path in sorted(dist.iterdir()):
    if not path.is_file() or path.name=='SHA256SUMS':continue
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    lines.append(f'{digest}  {path.name}')
(dist/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
print(f'Verified {len(catalog["examples"])} examples; checksummed {len(lines)} release files')
