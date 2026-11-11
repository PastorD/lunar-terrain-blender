#!/usr/bin/env bash
# Requires Harmonic development libraries and a normal network-capable host.
set -euo pipefail
lunar_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
lunar_package_dir="$(cd -- "${1:-$lunar_script_dir}" && pwd)"
export GZ_SIM_RESOURCE_PATH="$lunar_package_dir/models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
mkdir -p "$lunar_package_dir/test_output"
g++ -std=c++17 -O2 "$lunar_script_dir/tests/camera_subscriber.cc" -o "$lunar_package_dir/test_output/camera_subscriber" \
  $(pkg-config --cflags --libs gz-transport13 gz-msgs10 gz-common5-graphics)
python3 "$lunar_script_dir/tests/server_smoke.py" "$lunar_package_dir"
