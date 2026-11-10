# Lunar Terrain 1.2 — Blender 5.2 validation

Validated on **8 September 2026** using the official Blender Foundation **bpy 5.2.1 LTS** runtime, **Python 3.13.15**, **NumPy 2.5.3**, on Linux with CPU Cycles. The extension requires Blender 5.2.0 or newer. Interactive mouse/keyboard UI behavior, GPU backends and other operating systems were not tested.

| Check | Result | Evidence |
| --- | --- | --- |
| ZIP installation | Installed using Blender's actual `extensions.package_install_files` operator into an isolated local repository; extension namespace, panel registration, cache and disable/re-enable pass | `tests/install_results.json` |
| Presets and hardware | Apollo 17, Connecting Ridge south pole and Chang’e-6 all build through the installed extension; Apollo also generates the rover and base | `tests/install_results.json` |
| Terrain and lifecycle | DEM units, exact-pole continuity, longitude wrapping, continuous mesh, positive winding, cancellation, staged failure cleanup, active-camera focus, zero populations and user-object preservation pass | `tests/results.json` |
| Solar disc | Camera-visible disc follows the Sun; effective diameter 6.5735 pixels versus approximately 6.578 expected; black sky away from it | `tests/results.json` |
| Opposition | Four linear-light ON/OFF render ratios at 0°, 0.25°, 10°, 60° agree with the scalar approximation within **0.00436%** | `tests/photometry_validation.json`, `tests/opposition_validation.csv` |
| Roughness | Eight rendered incidence/emergence/azimuth configurations, through 88° incidence, agree with the scalar approximation within **0.000143%** | `tests/roughness_results.json` |
| Numerical limits | 180 configurations through 89.9° are finite and nonnegative; reciprocity error <5×10⁻¹⁶; zero-roughness closed-form error <6×10⁻¹⁶; unlit and optional CBOE limits pass | `tests/roughness_results.json` |
| Appearance controls | Switching appearances preserves geometry, camera and manually edited Sun; regional lookup preserves exposure and rejects missing polar coverage | `tests/roughness_results.json` |
| Rock meshes | All 24 prototypes validate and retain unit equivalent projected area; near meshes have 2,562 vertices / 5,120 triangles; small/far meshes have 42 / 80 | `tests/rock_detail_results.json` |
| Existing-scene migration | 24 prototypes upgraded in each of three original scenes; terrain/placement vertex signatures, cameras, Sun, Hapke parameters and exposure preserved; repeat upgrade is idempotent | `tests/migration_results.json` |
| Standalone scenes | All four scenery files reopen and render without registering the add-on; nine valid shader drivers per scene; zero external file dependencies | `tests/portability_results.json` |

## Render inspection

The Apollo surface (1100×1100), outpost (1800×1100), Chang’e-6 surface (1280×960), and new rock close-up (1200×900) were rendered in Blender 5.2.1 with **48 Cycles samples and denoising**, and visually inspected. Near rocks show chipped geometry, broken fracture lines, pits and grain. The terrain and lighting keep the previous Apollo/Chang’e appearance settings. Standalone smoke renders use 20% resolution and eight samples.

The rock close-up uses deliberately placed 1.5 m, 0.64 m and 0.27 m rocks to make their surfaces inspectable. These shapes and textures are procedural interpretations, not scanned rocks or measured mineral maps. Shadows use Cycles occlusion; the rocks retain the same Hapke model as the soil.

## Scope and provenance

The native-node shader is a single-Sun direct-light approximation. Indirect illumination, multiple lights and finite-disc angular integration remain approximate. Numerical agreement verifies implementation of the stated approximation, not a laboratory validation or a calibrated photometric inversion of the supplied processed mission photographs.

Regional Apollo and Chang’e LROC 566 nm parameter values are unchanged from version 1.1. The adjusted south-pole 5 m DEM and Apollo 17 SLDEM pack remain bundled. Chang’e-6 uses real LOLA 64 pixels/degree context, approximately 474 m posting. Relief below DEM resolution, rocks and small craters are synthetic.

The previous release's image-brightness comparison is retained as `tests/appearance_check_v1_1.json`, with its historical validation narrative in `tests/VALIDATION_1_1.md`; it is not a new 5.2 photometric calibration. Other original data-provenance and converter reports are retained with their original scope. See `BLENDER_52_UPDATE.md` for the exact reproduction commands.
