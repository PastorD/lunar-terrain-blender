"""Package validated atlas, extension, polar scenes and reproducible DEM assets."""
from pathlib import Path
import hashlib,json,shutil,tomllib,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/atlas'
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def main():
    version=tomllib.loads((ROOT/'lunar_terrain/blender_manifest.toml').read_text())['version'];OUT.mkdir(parents=True,exist_ok=True)
    installer=OUT/f'lunar_terrain-{version}.zip';assert installer.is_file()
    for file,target in [('docs/index.html','Lunar_Atlas.html'),('build/atlas/Polar_Context.png','Polar_Context.png'),('POLAR_SITES.md','POLAR_SITES.md'),('build/atlas/Atlas_Browser_validation.json','Atlas_Browser_validation.json'),('build/atlas/Atlas_Desktop.png','Atlas_Desktop.png'),('build/atlas/Atlas_Global.png','Atlas_Global.png'),('build/atlas/Atlas_Mobile.png','Atlas_Mobile.png'),('tests/install_results.json','Extension_Install_validation.json'),('tests/install_upgrade_results.json','Extension_Upgrade_validation.json'),('tests/extension_package_results.json','Extension_Package_validation.json'),('build/polar_sources/validation.json','Polar_DEM_validation.json')]:
        shutil.copy2(ROOT/file,OUT/target)
    for name in ('VIPER_Mons_Mouton','Nobile_Rim_2','Malapert_Massif'):
        validation=ROOT/'build/polar_examples'/(name+'_validation.json');result=json.loads(validation.read_text());assert result['passed'] and not result['draft']
        for source in (ROOT/'examples'/(name+'.blend'),ROOT/'examples/renders'/(name+'.png'),validation):shutil.copy2(source,OUT/source.name)
    records=[];archive=OUT/f'lunar-terrain-data-{version}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted((ROOT/'lunar_terrain/data').rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or p.suffix in ('.partial','.pyc'):continue
            rel=p.relative_to(ROOT).as_posix();z.write(p,rel);records.append(dict(path=rel,sha256=sha(p),bytes=p.stat().st_size))
    manifest=dict(version=version,repository='PastorD/lunar-terrain-blender',extension_sha256=sha(installer),data_archive=dict(name=archive.name,url=f'https://github.com/PastorD/lunar-terrain-blender/releases/download/v{version}/{archive.name}',sha256=sha(archive),bytes=archive.stat().st_size),data_files=records)
    (OUT/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copy2(ROOT/'lunar_terrain/data/provenance.json',OUT/'provenance.json')
    (OUT/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
    print('ATLAS RELEASE PACKAGED',len(records),'data files',flush=True)
if __name__=='__main__':main()
