#!/usr/bin/env bash
set -euo pipefail
lunar_package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export GZ_SIM_RESOURCE_PATH="$lunar_package_dir/models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
lunar_world="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["model_id"].removesuffix("_terrain"))' "$lunar_package_dir/export_manifest.json")"
exec gz sim -r "$lunar_package_dir/worlds/$lunar_world.sdf" "$@"
