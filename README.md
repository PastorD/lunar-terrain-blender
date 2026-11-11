# Lunar Terrain for Blender

Generate lunar landscapes from real elevation data, with continuous levels of detail, fractured rocks, degraded craters and Hapke-style opposition shading.

**Blender 5.2+ · Version 1.5.0 · Tested with Linux bpy 5.2.1 LTS**

[Download the extension](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/lunar_terrain-1.5.0.zip) · [All example scenes](https://github.com/PastorD/lunar-terrain-blender/releases/tag/v1.5.0) · [User guide](USER_GUIDE.md) · [Report an issue](https://github.com/PastorD/lunar-terrain-blender/issues)

![Chandrayaan-3 terrain rendered in Cycles](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/Chandrayaan3_Surface.png)

## Start with a scene

Download one `.blend`, open it in Blender and press **F12**. Materials, geometry, lighting and cameras are already included. The extension is needed to regenerate terrain; it is not needed to render the examples.

| Example | Download | What it contains |
| --- | --- | --- |
| Chandrayaan-3 / Shiv Shakti | [Chandrayaan3_Surface.blend](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/Chandrayaan3_Surface.blend) | Neutral Pragyan NavCam-inspired ground, native 3 m local DEM; no Vikram model |
| Blue Ghost / Mare Crisium | [BlueGhost_Surface.blend](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/BlueGhost_Surface.blend) | Cool low-Sun surface study, native 3 m local DEM |
| Apollo 17 surface | [Apollo17_Surface.blend](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/Apollo17_Surface.blend) | Bright gray soil and a Taurus–Littrow landscape |
| Apollo 17 concept outpost | [Apollo17_Outpost.blend](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/Apollo17_Outpost.blend) | Editable concept rover, habitats, solar panels and astronaut |
| Chang'e-6 surface | [ChangE6_Surface.blend](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/ChangE6_Surface.blend) | Warm regolith appearance study |
| Rock detail | [Rock_Detail.blend](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/Rock_Detail.blend) | Close-up fractured rocks and surface material |
| Opposition check | [Hapke_Opposition_Check.blend](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/Hapke_Opposition_Check.blend) | A photometric inspection scene |

Apollo and Chang'e example geometry preserves the earlier 1.2 appearance studies. Rebuild those examples with the 1.5 extension to use its newer native DEM selection. Blue Ghost and Chandrayaan-3 scenes already contain their native local crops.

## Use the examples in Gazebo

All seven examples also have a Gazebo Harmonic export: Apollo 17 surface and outpost, Chang'e-6, Blue Ghost, Chandrayaan-3, the rock close-up and the opposition diagnostic. Each package contains a local SDF world, textured visual meshes, separate collisions, lunar gravity and a launcher.

[Gazebo downloads](https://github.com/PastorD/lunar-terrain-blender/releases/tag/gazebo-v1.0.0) · [Gazebo guide and limitations](gazebo/README.md) · [Build/test status](https://github.com/PastorD/lunar-terrain-blender/actions/workflows/gazebo-examples.yml)

Gazebo uses **PBR approximations**, so the Blender Hapke opposition effect does not transfer. The diagnostic export has identical PBR panels; use the original `.blend` to inspect the Hapke response. Outpost hardware is static geometry. The build workflow tests each export before publishing it.

## Install the generator

1. Download **[lunar_terrain-1.5.0.zip](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/lunar_terrain-1.5.0.zip)**. Keep it zipped. GitHub's automatically generated **Source code** archive is not the installable extension.
2. In Blender, open **Edit → Preferences → Get Extensions → menu → Install from Disk**. Select the extension ZIP and enable it.
3. Start with an empty scene. In the 3D View, press **N** and open **Lunar**.
4. Choose a location, click **Apply location and look**, then **Build / Rebuild Lunar Terrain**.
5. Press **F12** to render. Use **Update Lighting and Materials** for appearance-only changes.

The installer includes offline elevation data and uses Blender's bundled Python and NumPy. No pip install is required. Enable Blender's **Allow Online Access** only when you want additional location data. See [installation and upgrades](EXTENSION_INSTALL.md).

## Location presets and DEM spacing

| Location | Native local grid | Wider context |
| --- | --- | --- |
| Apollo 17 | LROC NAC 2 m | SLDEM2015 59.225 m |
| Chang'e-6 | LROC NAC 4 m | LOLA 473.8 m / 1895 m offline |
| South pole / Connecting Ridge | LROC NAC 2 m where valid | Adjusted LOLA 5 m / 80 m |
| Blue Ghost 1 | LROC NAC 3 m | SLDEM2015 59.225 m |
| Chandrayaan-3 | LROC NAC 3 m | LOLA 473.8 m |

Other coordinates use the supported DEM catalogue, downloads and offline fallback. The panel reports **actual loaded grid spacing** separately from procedural mesh spacing. A 0.1 m mesh does not imply a measured 0.1 m DEM. Missing cells and dataset boundaries blend into available coarser data. Default terrain radius is 20 km, with lunar curvature enabled.

## Appearance gallery

| Concept outpost | Blue Ghost study |
| --- | --- |
| ![Apollo-style outpost](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/Apollo17_Outpost.png) | ![Blue Ghost surface](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/BlueGhost_Surface.png) |

![Chang'e-6 surface study](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.5.0/ChangE6_Surface.png)

These images are renders of the downloadable scenes, not mission photographs.

## Physical scope

- Real DEM elevations supply broad terrain; sub-DEM rocks, small craters and grain are procedural.
- Hapke terms use regional LROC photometric priors, with art-directed reference appearances. The shader is a **single-Sun view-dependent Diffuse BSDF approximation**, not a full custom path-tracer BRDF.
- Cast shadows are rendered by Cycles. A camera-visible Sun disc follows the Sun direction.
- Lighting is manually controlled; location selection does not calculate a date-dependent ephemeris.
- Rock/crater abundance is not a measured population for every selected site. See the [user guide](USER_GUIDE.md), [photometry](APPEARANCE_UPDATE.md), [DEM details](DEM_UPDATE.md) and [Chandrayaan-3 notes](CHANDRAYAAN3.md).

## Source and development

Large DEM arrays and `.blend` files are release downloads, so cloning this repository stays small. To restore the exact versioned data needed for a source build:

```sh
git clone https://github.com/PastorD/lunar-terrain-blender.git
cd lunar-terrain-blender
python3 tools/fetch_release_data.py
blender --command extension validate lunar_terrain
blender --command extension build --source-dir lunar_terrain --output-filepath lunar_terrain-1.5.0.zip
```

The download helper uses Python's standard library, checks the pinned SHA-256 and verifies every data member. For an offline build, download `lunar-terrain-data-1.5.0.zip` from the release and run `python3 tools/fetch_release_data.py --archive /path/to/lunar-terrain-data-1.5.0.zip`.

Existing test results record Linux, official bpy 5.2.1, headless CPU validation, including installation, disable/re-enable, an upgrade from 1.4.0, all five sites offline and a Chandrayaan-3 render. They do not claim interactive UI, GPU, Windows or macOS validation. See [validation records](tests/install_results.json).

## License and attribution

Source code is **GPL-3.0-or-later**; see [LICENSE](LICENSE). Third-party data retain their own terms: the derived Chang'e-6 crater catalogue is **CC BY 4.0**, and elevation/photometric data retain their documented source attribution. See [data provenance](lunar_terrain/data/PROVENANCE.md), [dataset manifest](lunar_terrain/data/provenance.json), and [source references](USER_GUIDE.md#sources-and-attribution).

The rover and base are original visualization concepts, not official Toyota/JAXA engineering models. No endorsement by NASA, ISRO, JAXA, CNSA or Firefly is implied. Mission photographs are linked as references, not redistributed. This release is distributed through GitHub; it is not listed in the official Blender Extensions catalogue.
