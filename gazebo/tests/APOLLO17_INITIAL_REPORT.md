# Apollo 17 Gazebo export — validation

Validation date: 10 November 2026.

The delivered asset is **Apollo17_Surface.blend exported to SDF/COLLADA**, with baked PBR textures. The source .blend was not modified.

| Component | Version used |
|---|---|
| Blender / official bpy | 5.2.1 LTS |
| Gazebo Sim (Harmonic installation) | 8.10.0 |
| Gazebo Common mesh loader | 5.7.1 |
| Gazebo Rendering | 8.2.2, Ogre2, software EGL |
| Gazebo Physics | 7.5.0, DART plugin |
| SDFormat | 14.8.0; exported schema 1.10 |

## Results

| Check | Result | Evidence / scope |
|---|---|---|
| Source .blend opens | PASS | Blender 5.2.1 LTS; source SHA-256 in manifest |
| SDF validation | PASS | `gz sdf -k`: Valid |
| Mesh loading | PASS | 26 visual batches; 6,802,176 triangles loaded by Gazebo Common |
| Ogre2 render | PASS | 900 × 900 PNG from the SDF camera; original scene geometry and baked textures visible |
| Terrain collision loading | PASS | 390,248 triangles, including per-vertex normals required by DART |
| Rock collision loading | PASS | 510,240 triangles; colliders derived from each matching visual prototype |
| Terrain drop probes | PASS | Five 0.2 m boxes landed and settled after 5 s of simulated time |
| Lunar gravity | PASS | After 1 s, free-fall z = 9.18919 m, vz = −1.62 m/s from an initial z = 10 m |
| Contacts | PASS | 35 contact records at the final physics step |
| Full `gz sim` server | BLOCKED | Local network interface discovery failed before simulation startup |
| GUI and ROS bridge | NOT TESTED | Require the server / normal host environment |
| Photometric equivalence to Hapke | NOT IMPLEMENTED | Export uses stock PBR; opposition response and small-rock shadow fidelity are not preserved |

The analytical free-fall height at 1 s is 9.19000 m. The measured 0.81 mm difference is consistent with the 1 ms discrete integration step. The probe is positioned outside the 20 km terrain disc so it cannot land on an unintended ground plane.

## Terrain collision approximation

At 1,500 reproducible XY points in a 300 × 300 m square around the origin, vertical ray intersections against the visual and simplified collision meshes differed by:

| Statistic | Error |
|---|---:|
| Mean | 1.445 mm |
| 95th percentile | 3.906 mm |
| Maximum sampled | 9.766 mm |

These are sampled Blender BVH comparisons, not a global error bound or a DEM accuracy estimate. They use float precision. Both surfaces are synthetic below the 59.2253 m source DEM cell spacing.

## Drop-probe results at 5 seconds

| Probe | Final centre height (m) | Final speed (m/s) |
|---|---:|---:|
| 0 | 0.102351 | 1.94e−9 |
| 1 | −0.099128 | 5.54e−7 |
| 2 | 0.189279 | 1.02e−9 |
| 3 | 0.452168 | 4.45e−6 |
| 4 | −0.437709 | 8.92e−6 |

These are world-frame centre heights, not box-to-ground clearances. Boxes can tilt on the uneven terrain. The assertions require finite positions above the local terrain and settled speed below 0.08 m/s. The CSV retains trajectories at 0.1 s intervals.

## What the offline tests mean

The physics harness constructs a world with Gazebo Physics/DART and attaches its COLLADA collision meshes with `AttachMeshShape`, the same path used by Gazebo Sim's Physics system. It advances actual rigid-body dynamics; it is not merely XML validation. The rendering harness loads the SDF, materials and camera into Gazebo Rendering/Ogre2 and captures an actual rendered frame.

The complete server uses Gazebo Transport. Its ZeroMQ local-interface discovery failed with `Operation not permitted (src/ip_resolver.cpp:542)`. The environment's automatic approval policy rejected a request to run outside that sandbox. No network restrictions were bypassed. Therefore a full server startup, interactive GUI and ROS bridge are not claimed as verified.

`test_server.sh` is supplied for a local server/camera smoke test. `tests/run_offline_tests.sh` reproduces the mesh, physics and rendering checks with Harmonic development packages installed.

The image is an approximate PBR rendering. It retains geometry and surface texture but is darker than the original AgX/Hapke render and has weak small-rock cast shadows. It should not be used as a calibrated lunar camera simulator. Real-time performance, traction, deformable soil and navigation accuracy were not measured.

Evidence: `tests/physics.log`, `tests/render.log`, `tests/sdf_validation.log`, `tests/drop_probe_results.csv`, `tests/gazebo_apollo17.png`, and `export_manifest.json`.
