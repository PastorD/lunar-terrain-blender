# Lunar Terrain 1.5.0 — Blender extension

Requires Blender 5.2 or newer. Use **lunar_terrain-1.5.0.zip** for installation.

## Install or update

1. If an earlier installation failed with the scene-registration error, restart Blender.
2. Open **Edit → Preferences → Get Extensions** and choose **Install from Disk** from the top-right menu.
3. Select the ZIP without extracting it. Keep **Enable on Install** selected. For an update, choose the same extension repository as the existing Lunar Terrain installation.
4. In **Preferences → Add-ons**, search for **Lunar Terrain** and check that version **1.5.0** is enabled.
5. In the 3D View, press **N**, open **Lunar**, choose a location, then click **Apply location and look** and **Build / Rebuild Lunar Terrain**.

The bundled native crops and fallback terrain work offline. To fetch finer elevation around another location, enable Blender’s **Allow Online Access** and the panel’s **Download finer DEM before building** option.

The extension includes its required data and uses Blender’s bundled NumPy. Normal installation needs no pip command or additional Python package.

## Changes in 1.5.0

Added Chandrayaan-3 / Shiv Shakti, neutral NavCam appearance, soil texture control, native 3 m DEM crop and linked photo catalogue. Corrected polar true-scale latitude handling. See CHANDRAYAAN3.md.

## Changes in 1.4.0

Added the Blue Ghost location and appearance, native 3 m DEM crop and 59.225 m context. See BLUE_GHOST.md.

## Extension packaging inherited from 1.3.2

- Corrected the network-permission description to meet Blender’s 64-character validation limit.
- Kept the extension ID **lunar_terrain**, so the package can update an existing installation in the same repository.
- Made the manifest the metadata source; removed the obsolete legacy add-on metadata.
- Added build exclusions for Python caches and temporary archives.
- Replaced manual installer packing with Blender’s official extension builder and strict validator.
- Retained the 1.3.1 registration fix, extension-specific writable DEM cache, and offline-access handling.

The renderer and terrain generator retain the existing implementation. Blue Ghost adds regional parameters and appearance settings.

## Rebuild from source

Inside the project’s lunar_terrain directory, using the Blender 5.2 executable:

~~~sh
blender --command extension validate
blender --command extension build --output-dir ..
blender --command extension validate ../lunar_terrain-1.5.0.zip
~~~

The project’s tools/package_release.py additionally refreshes data provenance, verifies ZIP integrity and Python syntax, and atomically replaces the output. It accepts --blender /path/to/blender, or discovers the official bpy wheel in the Python environment running it. That developer script needs NumPy; it is outside the installable extension.

The complete/source archives also contain tests/install_extension.py. Run it with the finished ZIP in Blender’s background Python mode. Its optional --upgrade-from argument exercises an update from an earlier ZIP and verifies settings and cache retention. Test records name the exact archive SHA-256 and runtime scope.

This package supports installation from disk. It has not been published to the public Blender Extensions catalogue.
