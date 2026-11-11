# Lunar examples for Gazebo Harmonic

Export all seven saved Blender 1.5.0 examples as local **SDF worlds, textured visual meshes and independent collision meshes**. Each package starts with `bash run.sh`; no Blender installation or Fuel downloads are needed to run it.

[Gazebo packages](https://github.com/PastorD/lunar-terrain-blender/releases/tag/gazebo-v1.0.0) · [Original Blender examples](https://github.com/PastorD/lunar-terrain-blender/releases/tag/v1.5.0) · [Build and test status](https://github.com/PastorD/lunar-terrain-blender/actions/workflows/gazebo-examples.yml)

## Examples

| Example | Gazebo package | Saved terrain extent |
|---|---|---|
| Apollo 17 surface | [Apollo17_Surface_Gazebo.zip](https://github.com/PastorD/lunar-terrain-blender/releases/download/gazebo-v1.0.0/Apollo17_Surface_Gazebo.zip) | 40 km diameter |
| Apollo 17 concept outpost | [Apollo17_Outpost_Gazebo.zip](https://github.com/PastorD/lunar-terrain-blender/releases/download/gazebo-v1.0.0/Apollo17_Outpost_Gazebo.zip) | 40 km diameter; rover, habitats, solar panels, astronaut |
| Chang'e-6 surface | [ChangE6_Surface_Gazebo.zip](https://github.com/PastorD/lunar-terrain-blender/releases/download/gazebo-v1.0.0/ChangE6_Surface_Gazebo.zip) | 20 km diameter |
| Blue Ghost surface | [BlueGhost_Surface_Gazebo.zip](https://github.com/PastorD/lunar-terrain-blender/releases/download/gazebo-v1.0.0/BlueGhost_Surface_Gazebo.zip) | 40 km diameter |
| Chandrayaan-3 surface | [Chandrayaan3_Surface_Gazebo.zip](https://github.com/PastorD/lunar-terrain-blender/releases/download/gazebo-v1.0.0/Chandrayaan3_Surface_Gazebo.zip) | 40 km diameter |
| Rock detail | [Rock_Detail_Gazebo.zip](https://github.com/PastorD/lunar-terrain-blender/releases/download/gazebo-v1.0.0/Rock_Detail_Gazebo.zip) | 200 m diameter; all three close-up rocks |
| Opposition check | [Hapke_Opposition_Check_Gazebo.zip](https://github.com/PastorD/lunar-terrain-blender/releases/download/gazebo-v1.0.0/Hapke_Opposition_Check_Gazebo.zip) | Two diagnostic panels; no DEM |

**The opposition check is a limitation demonstration in Gazebo:** both panels use identical PBR materials. Stock Ogre2 does not implement the Blender Hapke shader, so the original `.blend` remains the opposition-effect reference.

The surface examples retain the exact saved geometry, rocks, source Sun direction and camera framing. These are terrain appearance studies; Chang'e-6, Blue Ghost and Chandrayaan-3 packages do not contain mission lander/rover models. The outpost contains original concept hardware, exported as static objects.

## Run a downloaded package

Extract the whole ZIP, enter its directory, and run:

```bash
bash run.sh
# Or a server with camera output and no GUI:
bash run.sh -s --headless-rendering
```

Use Gazebo Harmonic / Sim 8. The launcher sets `GZ_SIM_RESOURCE_PATH` to the package's `models` directory. The package README gives its model URI, world filename and camera topic. To use a model in another world, add that models directory to the resource path and include its `model://...` URI. Set lunar gravity to `0 0 -1.62` and provide lighting.

All assets use metres and Z-up. Terrain scenes retain the source local east/north/up coordinates and lunar curvature. The camera sensor preserves source aspect ratio (up to 1200 pixels on the longest edge). The orthographic diagnostic is exported with a perspective camera matching its flat-panel framing; this is recorded explicitly.

## Build any or all examples

Install the official bpy wheel in a separate **Python 3.13** environment:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r gazebo/requirements-blender.txt
.venv/bin/python gazebo/build_examples.py build --example change6
# All seven:
.venv/bin/python gazebo/build_examples.py build --example all
```

The helper downloads each unchanged `.blend` from v1.5.0 and verifies its size and SHA-256 against `examples.json`. Existing mismatching files are rejected. For sources already on disk, add `--sources-dir /path/to/examples`. Output goes to `build/gazebo/<example-id>`; use a new directory for a rebuild. It never overwrites the source `.blend`.

To export a modified Lunar Terrain scene directly:

```bash
.venv/bin/python gazebo/scripts/export_blender.py custom.blend build/custom \
  --model-id custom_terrain --title 'Custom lunar terrain'
python3 gazebo/scripts/make_worlds.py build/custom
```

The direct exporter supports the Lunar Terrain schema, yaw-only scatter instances, one Sun, material-slot hardware meshes, evaluated modifiers and fonts. It is not a general Blender-to-Gazebo converter. The launchers and tests can be copied from `gazebo/` into the resulting package.

## Geometry, textures and physics

- Full saved terrain visual geometry is split at 128 m into near/far batches with matching normals. Smaller scenes need only one batch.
- All scattered rocks are retained. Detailed scatter prototypes simplify from 5120 to 1280 faces; small prototypes retain 80 faces.
- The three close-up rocks retain full geometry and use individual 2048-pixel albedo/normal maps.
- Ground collisions use 16% of source faces. Rocks at least 15 cm across have matching simplified colliders; smaller pebbles are visual only.
- Hardware parent transforms, modifiers, material slots, colors, metallic and roughness values are exported. Hardware is static and has mesh collisions. Small procedural hardware bump textures are omitted.
- Regolith uses a repeating 64 m / 4096-pixel albedo and tangent-normal patch. Scatter rocks use 512- or 256-pixel maps. These textures approximate the source tint/fractures without baking Sun lighting or cast shadows.
- Every package records source checksums, DEM provenance/settings, actual extent, geometry counts and collision-height samples in `export_manifest.json`.

The saved Apollo and Chang'e scenes predate the generator's newer native DEM selection. Export does **not** replace their geometry with a new DEM. Blue Ghost and Chandrayaan-3 retain their existing native local data. Procedural mesh spacing is not measured DEM resolution.

**Hapke angular response, opposition brightening, Blender exposure/AgX, the visible Sun disc and Cycles shadow fidelity do not transfer to stock PBR.** The export is not a calibrated lunar camera simulator. Subpixel grain is lost, repeated ground textures can become visible, and small-rock cast shadows can be weaker than in Cycles. A custom Gazebo shader/rendering plugin would be needed for Hapke.

Physics is rigid-body contact with constant local gravity and illustrative friction 0.8, not deformable regolith or validated wheel-soil traction. No rover joints/controllers, sinkage or terramechanics model is supplied. Do not drive outside a package's actual terrain extent.

## Tests and release process

The workflow builds all seven scenes independently with bpy 5.2.1 and Gazebo Harmonic. Publishing requires all seven to pass:

1. Gazebo Common mesh loading and an actual Ogre2 rendered frame.
2. Gazebo Physics / DART mesh attachments, five falling boxes settling after 5 s, final contacts, and a lunar free-fall check at 1 s.
3. A full `gz sim` headless server/camera smoke test producing image frames without reported errors.

The initial Apollo-only test report is preserved in `tests/APOLLO17_INITIAL_REPORT.md`; its full server test was blocked by local interface-discovery restrictions. New release reports are generated from the hosted workflow's actual results and do not inherit that earlier status.

To reproduce on a normal Linux host with Harmonic development packages and a C++17 compiler:

```bash
bash gazebo/tests/run_offline_tests.sh build/gazebo/change6
bash gazebo/test_server.sh build/gazebo/change6
python3 gazebo/build_examples.py package --example change6
```

`environment.yml` describes the conda-forge Gazebo environment used in CI. For conda builds, activate that environment and add its library directory to `LD_LIBRARY_PATH`. For CPU-only EGL rendering, set `LIBGL_ALWAYS_SOFTWARE=1`. A GPU is preferable for interactive use. GUI operation, ROS bridging, real-time performance and mission-specific photometric accuracy are not asserted by these tests.

The release contains one ZIP and actual Gazebo preview per example, per-example validation JSON, exporter source, and `SHA256SUMS`. It is a separate `gazebo-v1.0.0` release so the latest Blender extension remains easy to find.

## Attribution

Code: GPL-3.0-or-later, see the repository LICENSE. Elevation data retain their documented NASA LOLA, SLDEM2015 and LROC source attribution; see `lunar_terrain/data/PROVENANCE.md`, the original Blender release and per-export manifests. Synthetic crater sampling derives from Zhao et al. (2025), [doi:10.1029/2025JE008960](https://doi.org/10.1029/2025JE008960), [Zenodo 14920942](https://doi.org/10.5281/zenodo.14920942), CC BY 4.0. Mission photographs are not redistributed. Concept hardware is not official Toyota/JAXA CAD, and no mission/agency endorsement is implied.

Gazebo primary references: [Common mesh loader](https://gazebosim.org/api/common/5/classgz_1_1common_1_1MeshManager.html), [headless rendering](https://gazebosim.org/api/sim/8/headless_rendering.html), [Sim Physics implementation](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/physics/Physics.cc).
