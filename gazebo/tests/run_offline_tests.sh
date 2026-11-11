#!/usr/bin/env bash
# A package path is mandatory when running from the source checkout.
set -euo pipefail
lunar_test_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
lunar_package_dir="$(cd -- "${1:-$lunar_test_source/..}" && pwd)"
lunar_test_dir="$lunar_package_dir/test_output"
mkdir -p "$lunar_test_dir"
g++ -std=c++17 -O2 "$lunar_test_source/render_export.cc" -o "$lunar_test_dir/render_export" \
  $(pkg-config --cflags --libs gz-rendering8 gz-common5-graphics sdformat14)
g++ -std=c++17 -O2 "$lunar_test_source/physics_export.cc" -o "$lunar_test_dir/physics_export" \
  $(pkg-config --cflags --libs gz-physics7 gz-physics7-mesh gz-plugin2-loader gz-common5-graphics sdformat14 gz-math7-eigen3)
python3 "$lunar_test_source/resolve_world.py" "$lunar_package_dir" "$lunar_test_dir/physics.sdf"
lunar_physics_lib="$(pkg-config --variable=libdir gz-physics7)/libgz-physics7-dartsim-plugin.so"
"$lunar_test_dir/physics_export" "$lunar_test_dir/physics.sdf" "$lunar_physics_lib" "$lunar_test_dir/drop_probe_results.csv" | tee "$lunar_test_dir/physics.log"
lunar_world="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["model_id"].removesuffix("_terrain"))' "$lunar_package_dir/export_manifest.json")"
"$lunar_test_dir/render_export" "$lunar_package_dir/worlds/$lunar_world.sdf" "$lunar_package_dir" "$lunar_test_dir/preview.png" | tee "$lunar_test_dir/render.log"
