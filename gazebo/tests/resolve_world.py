"""Resolve local model:// references for the standalone physics harness."""
from pathlib import Path
import json,sys,xml.etree.ElementTree as E
p=Path(sys.argv[1]).resolve();d=json.loads((p/'export_manifest.json').read_text())
world=d['model_id'].removesuffix('_terrain')
t=E.parse(p/'worlds'/f'{world}_test.sdf');w=t.getroot().find('world')
for include in list(w.findall('include')):
    uri=include.findtext('uri')
    if not uri.startswith('model://'):raise ValueError('Only local models are allowed')
    w.remove(include);w.insert(0,E.parse(p/'models'/uri[8:]/'model.sdf').getroot().find('model'))
for n in t.getroot().iter('uri'):
    if n.text.startswith('model://'):n.text=str(p/'models'/n.text[8:])
E.indent(t);t.write(sys.argv[2],encoding='utf-8',xml_declaration=True)
