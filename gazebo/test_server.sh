#!/usr/bin/env bash
# Full Gazebo Sim server/camera smoke test; separate from DART assertions.
set -euo pipefail
lunar_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
lunar_package_dir="$(cd -- "${1:-$lunar_script_dir}" && pwd)"
export GZ_SIM_RESOURCE_PATH="$lunar_package_dir/models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
mkdir -p "$lunar_package_dir/test_output"
python3 - "$lunar_package_dir" <<'PY'
import json,sys,xml.etree.ElementTree as E
from pathlib import Path
p=Path(sys.argv[1]);d=json.loads((p/'export_manifest.json').read_text())
w=d['model_id'].removesuffix('_terrain');t=E.parse(p/'worlds'/f'{w}_test.sdf')
c=t.find('.//sensor/camera');c.find('image/width').text='320';c.find('image/height').text='240'
sensor=t.find('.//sensor');sensor.find('update_rate').text='2'
save=E.SubElement(c,'save',enabled='true');E.SubElement(save,'path').text=str(p/'test_output/frames')
t.write(p/'test_output/server_test.sdf',encoding='utf-8',xml_declaration=True)
PY
timeout 600 gz sim -s -r --headless-rendering --iterations 1500 -v 3 \
  "$lunar_package_dir/test_output/server_test.sdf" \
  > "$lunar_package_dir/test_output/server.log" 2>&1
python3 - "$lunar_package_dir" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])/'test_output'
frames=list((p/'frames').rglob('*.png'));log=(p/'server.log').read_text(errors='replace')
assert frames,'No camera frames; inspect test_output/server.log'
assert '[Err]' not in log,'Gazebo reported errors; inspect test_output/server.log'
(p/'server_result.json').write_text(json.dumps(dict(passed=True,frames=len(frames),iterations=1500,scope='Full gz sim server, mesh loading and camera output. Contacts/gravity tested separately.'),indent=2)+'\n')
print(f'SERVER SMOKE PASS: {len(frames)} frames.')
PY
