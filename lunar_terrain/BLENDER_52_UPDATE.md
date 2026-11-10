# Blender 5.2 and rock-detail update

Lunar Terrain **1.2.0** targets Blender **5.2**, with compatibility checks performed in the Blender Foundation **5.2.1 LTS** Python module. The extension minimum is 5.2.0. Blender 4.x is no longer a supported target for this release.

## Changes

- Uses Blender 5.2 material and world node trees directly; removes deprecated `use_nodes` accesses.
- Retains the Apollo and Chang’e regional Hapke parameters, exposure presets and continuous terrain generator.
- Nearby rocks at least 0.15 m across, within three near-detail radii, use 2,562 vertices / 5,120 triangles per prototype. Smaller or more distant rocks retain 42 vertices / 80 triangles. All 24 prototypes remain shared instances.
- Large-rock meshes now have coherent chipped surfaces and shallow broken stress fractures. Fine pits and grain use world-metre texture coordinates. Broken surface fissures, restrained mineral mottling and dust-colored Hapke shading add visible close-up detail without a glossy coating.
- Fracture and grain bump fade when their projected footprint becomes too small. The original exponential abundance sampler and projected-area normalization are retained.
- **Rocks and worn craters → Upgrade Rock Detail** upgrades existing owned rock prototypes in place, using the original generation seed. It preserves terrain, rock placements, camera, manual Sun rotation/energy and current exposure. Rebuilds use the new rocks automatically.

These rock shapes and textures are procedural interpretations of the supplied mission pictures. They do not encode measured mineral composition or a photogrammetric reconstruction. The material retains the existing single-Sun Hapke approximation and its documented indirect-light limitations.

## Installation

In Blender 5.2, open **Edit → Preferences → Get Extensions → Install from Disk** and select `Lunar_Terrain-1.2.0.zip`. Enable Lunar Terrain; the panel is in **3D View → N → Lunar**. For an existing scene, use **Upgrade Rock Detail** once. The full project includes the upgraded Apollo and Chang’e scenes and a `Rock_Detail.blend` close-up study.

## Reproducing checks

Normal use needs no pip installation. For the optional Linux headless workflow, create a Python 3.13 environment and install `requirements-validation.txt`. The official `bpy==5.2.1` package contains the actual Cycles renderer and Blender extension manager.

Run from the project root, using that environment's `python`:

```sh
python tests/install_extension.py /absolute/path/Lunar_Terrain-1.2.0.zip
python tests/integration.py
python tests/photometry.py
python tests/roughness.py
python examples/rock_detail.py
python examples/migrate_blender52.py
python tests/portability.py
```

The last two example scripts save and render the included scene files. `roughness.py` uses the diagnostic scene produced by `photometry.py`; keep that order. For the Blender desktop executable, use `blender -b --python SCRIPT`; pass the installation archive after `--`. `VALIDATION.md` and `tests/*results.json` record the completed release's actual checks and scope.

Runtime source: [Blender Foundation bpy 5.2.1](https://pypi.org/project/bpy/5.2.1/), released 25 August 2026. Validation covers Linux CPU rendering and extension operator registration, not GPU backends or interactive mouse/keyboard UI operation.
