# Lunar Terrain 1.5.0 — validation

The current release adds Chandrayaan-3 / Shiv Shakti, its native 3 m DEM, neutral NavCam appearance and reference catalogue.

- `tests/polar_scale_results.json`: forward and inverse polar coordinates checked against independent PROJ in both hemispheres, including −69.3° true-scale latitude. Valid 3 m cells load at the origin, elevation approximately 532.50 m.
- `tests/chandrayaan3_results.json`: actual 1024²/64-sample CPU Cycles render, nonzero rocks/craters, regional Hapke prior, and all four appearance changes preserving terrain, camera and Sun. Soil texture gain resets to 1 for existing looks.
- `tests/extension_package_results.json`: official extension builder/validator, ZIP integrity, Python syntax and exact archive hash.
- `tests/install_results.json`: finished ZIP installed offline through Blender's real extension operator; all five location presets, clear and disable/re-enable.
- `tests/install_upgrade_results.json`: update from 1.4.0 preserving latitude, seed, existing enum selections and DEM cache. Class checks account for the previous 17 and new 18 classes.
- `tests/registration_results.json`: restricted import/register/unregister and re-enable without accessing scenes during registration.

Runtime: official Linux bpy 5.2.1, headless CPU. No interactive GUI or GPU validation is claimed. Photograph matching is visual, not radiometric. The full registered PRADAN archive was not enumerated.

## Earlier release evidence

# Lunar Terrain 1.4.0 — validation

Version **1.4.0** adds the Blue Ghost location/look and native DEM crop. `tests/blue_ghost_results.json` records a real Cycles surface render, nonzero rock/crater populations, the loaded 3 m grid, regional Hapke priors, and appearance changes preserving mesh data, camera and Sun. `examples/blue_ghost.py` reproduces the study. Existing Apollo/Chang'e photometric definitions are unchanged.

The finished extension passes the official builder/validator and the exact-ZIP installer tests. `tests/install_results_1.4.0.json` exercises all four previous presets. `tests/install_upgrade_results_1.4.0.json` checks upgrade from 1.3.2, including settings/cache retention. Results use the official Linux bpy 5.2.1 runtime; no interactive GUI or GPU validation is claimed.

## Earlier extension packaging

Version **1.3.2** adds strict extension packaging. The 1.3.1 network permission reason was 71 characters; Blender’s validator permits at most 64. The corrected manifest and ZIP are built and validated with the official Blender 5.2.1 extension CLI. Python syntax and ZIP integrity are also checked. The build publishes its output only after these gates pass.

Release evidence is recorded in:

- `tests/extension_package_results_1.3.2.json`: official build/validation, ZIP integrity, Python syntax and archive hash.
- `tests/install_results_1.3.2.json`: actual ZIP installation with online access disabled, three preset builds, clear and disable/re-enable.
- `tests/install_upgrade_results_1.3.2.json`: installation of the saved 1.3.1 ZIP followed by a 1.3.2 update in the same extension repository; checks latitude, seed, cache and idle-state retention.
- `tests/registration_results_1.3.2.json`: restricted import/register/unregister, idle defaults and setting retention.

Installation tests assert Blender’s actual `_RestrictData` and `_RestrictContext` during every class registration. The official Linux bpy wheel requires a test-only module-alias bridge for this; the extension does not modify Blender internals. This is **headless Linux CPU validation**, not an interactive GUI or GPU test. Each installer test records the SHA-256 of its input ZIP.

Version **1.3.1** reproduces and fixes the 1.3.0 `_RestrictData.scenes` failure. Restricted import/register/unregister and re-enable now pass (`tests/registration_results_1.3.1.json`). The actual ZIP installation test enforces `_RestrictData` / `_RestrictContext` on every Lunar class registration, correcting the module-alias gap in the earlier headless check. See `INSTALLATION_FIX.md`.

## Earlier DEM validation

The 1.3.0 native-data layer was validated with official **bpy 5.2.1**, Python 3.13.15 and NumPy 2.5.3 on Linux. Results are reproducible using the scripts and JSON records in `tests/`.

| Check | Result | Evidence |
| --- | --- | --- |
| Native preset builds | Apollo 17 2 m, Chang’e-6 4 m, Connecting Ridge 2 m; 31,308 triangles each; finite meshes; unrelated geometry retained | `blender_dem_results.json` |
| Independent PDS decode | 64 original cells at each of three sites match Rasterio/GDAL exactly; pixel-centre coordinate error 0 m | `native_dem_results.json` |
| NASA BigTIFF | Original 10 m polar float32 data with Deflate floating-point predictor match GDAL exactly | `native_dem_results.json` |
| Crop overlaps | Affine-plane seam error 0.00003466 m, below the 0.0001 m float32 tolerance | `native_dem_results.json` |
| Missing data and boundaries | NoData fallback, longitude wrapping, exact-pole continuity, range-response refusal and transfer budget pass | `native_dem_results.json` |
| JAXA live download | Label-verified 32 MiB full-tile fallback passes; native grid 7.40316172467 m | `native_dem_results.json` |
| Map | Chromium 152; all three coordinate queries return 2/4/2 m; no JavaScript errors or page overflow at 360 px | `map_browser_results.json` |
| 1.3.1 ZIP | Actual Blender extension installation, three sites, outpost, 40 km elevation transects, rock update, clear, disable/re-enable | `install_results_1.3.1.json` |

The installer test records the SHA-256 of the exact installer it tested. No new GPU or interactive Blender UI checks are claimed. Previous Hapke, rocks, renders and lifecycle tests remain historical 1.2 evidence in `VALIDATION_1.2.md`; those images were not re-rendered for the DEM update.
