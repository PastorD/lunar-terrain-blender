# Lunar Terrain 1.5.0

First public GitHub release of the existing Blender 5.2+ extension and its example scenes. The installable ZIP is unchanged from the recorded 5.2.1 validation build.

## Choose your download

- **Generate terrain:** download `lunar_terrain-1.5.0.zip`, keep it zipped, then use Blender → Preferences → Get Extensions → Install from Disk. Offline DEMs are included; no separate data pack is needed for installation.
- **Render immediately:** download any `.blend` below, open it and press F12. The extension is only needed for regenerating terrain.
- **Develop from source:** clone the repository and run `python3 tools/fetch_release_data.py`. `lunar-terrain-data-1.5.0.zip` contains the separate data needed for source builds; it is not a Blender extension.
- **Verify downloads:** use `SHA256SUMS.txt`.

## Included scenes

Chandrayaan-3, Blue Ghost, Apollo 17 surface, Apollo 17 concept outpost, Chang'e-6 surface, rock detail and an opposition-effect check.

Chandrayaan-3 and Blue Ghost include native 3 m local DEMs. Apollo/Chang'e scenes preserve their earlier appearance studies; rebuild with the extension to use the newer native grids. The Chandrayaan-3 scene does not include a Vikram lander model.

## Features

- Five location presets, selectable latitude/longitude, actual DEM resolution reporting and offline fallback.
- Continuous multiresolution terrain with lunar curvature, detailed instanced rocks and procedural small craters.
- Apollo, Chang'e, Blue Ghost and Pragyan NavCam reference appearances.
- Regional LROC Hapke priors, a single-Sun shading approximation and a camera-visible Sun disc.
- Version 1.5 corrects polar true-scale latitude handling and adds Chandrayaan-3 / Shiv Shakti.

## Compatibility and validation

Requires Blender 5.2+. Recorded validation used official Linux bpy 5.2.1 LTS, headless CPU, and covers installation, disable/re-enable, upgrading from 1.4.0, all five sites offline and rendering. Interactive UI, GPU, Windows and macOS validation are not claimed. SHA-256 checks preserve the tested extension build.

Source: GPL-3.0-or-later. Third-party data keep the licenses and credits in the repository. These are visualization scenes, not exact mission reconstructions or calibrated camera inversions.
