# Lunar Terrain 1.3.1 — Blender registration fix

Version 1.3.0 could fail to enable in Blender 5.2.1 with:

```text
'_RestrictData' object has no attribute 'scenes'
```

The cause was a scene loop in `register()` that reset the temporary `busy` flag. Blender restricts `bpy.data` and `bpy.context` while registering an add-on. Version 1.3.1 removes that unnecessary loop: the flag already defaults to `False`, and normal job completion/cancellation resets it. Registration now declares classes and the scene property without reading scene data.

Version 1.3.2 includes this correction and fixes strict extension-manifest validation; see [EXTENSION_INSTALL.md](EXTENSION_INSTALL.md).

## Install the correction

1. Restart Blender to clear classes left by the failed registration attempt.
2. Open **Edit → Preferences → Get Extensions → menu → Install from Disk**.
3. Select **lunar_terrain-1.4.0.zip** and enable Lunar Terrain. It uses the same extension ID as 1.3.0, so install it into the same repository to update the existing extension.
4. Open **3D View → N → Lunar**. Saved scenes and native DEM controls use the same settings as 1.3.0.

No DEM, Hapke, rock, crater, terrain or camera behavior is changed by this patch.

## Regression checks

The original 1.3.0 code was reproduced under Blender’s actual `_RestrictData` and `_RestrictContext` objects and raised the exact error above. The corrected version passes restricted import, registration, unregistration and re-enabling, while retaining scene settings and the default idle state.

The earlier headless installation test was insufficient for this issue. In the official bpy 5.2.1 wheel used here, the restriction helper retained a different `bpy` module instance from the one imported by the add-on. The new tests point Blender’s own restriction manager at the add-on’s module and explicitly assert that its data and context are restricted during class registration. This adjustment is confined to the test harness; no Blender files or internals are modified by the add-on.

`tests/install_extension.py` tests the actual ZIP through Blender’s extension installer, checks restricted registration on both install and re-enable, builds all three presets, and records the archive SHA-256 in `tests/install_results.json`. `tests/registration_restriction.py` is the focused regression test. `tests/registration_130_reproduction.json` records the failing 1.3.0 case.

Validation uses the official Linux bpy 5.2.1 runtime with the registration restrictions enforced. It is not an interactive GUI or GPU test.
