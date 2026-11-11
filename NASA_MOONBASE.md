# NASA Moon Base — Connecting Ridge target-region study

This example uses **Shackleton Connecting Ridge**, the target region NASA names
for Blue Origin's Blue Moon Mark 1, an early Moon Base mission. NASA's event page,
updated October 21, 2026, lists the mission in **2027**. Checked November 10, 2026.

The scene origin is **89.4632° S, 137.49° W (222.51° E)**: the **R01 / Connecting
Ridge regional reference point** in NASA's *Lunar Surface Data Book*, ACD-50044
Revision A, Table A2-2, printed page 58. This is **not a confirmed touchdown
coordinate, landing ellipse, or finalized permanent base site**. NASA continues
to study several south-polar areas for its broader Moon Base. No landing-safety
assessment is implied.

## Download and use

[Download Blender and Gazebo files](https://github.com/PastorD/lunar-terrain-blender/releases/tag/moonbase-v1.0.0).

Open `NASA_MoonBase_Connecting_Ridge.blend` in Blender 5.2.1 or later and press F12.
The extension is not needed to render the saved geometry and materials. The
default camera is `Lunar • surface camera`, at 1.8 m eye height. Select
`Moon Base • regional overview` and make it active for the oblique context view.
`Lunar • look at Sun` provides the existing camera-visible solar-disc check.
All cameras use the same terrain and lighting.

| Component | Source or setting |
| --- | --- |
| Local terrain | LROC NAC `ESALL_CR1`, native **2 m grid** at the reference point |
| Wider terrain | Available adjusted LOLA context; **80 m grid at sampled 20 km perimeter** |
| Extent | **20 km radius / 40 km diameter**, lunar curvature enabled |
| Foreground | 0.12 m mesh spacing within a 24 m detail radius; procedural below the DEM grid |
| Rocks and craterlets | Existing seeded analogue populations and fractured, dust-coated rock materials |
| Photometry | Apollo 17 regional Hapke analogue, explicitly not a measured polar fit |
| Sun | Azimuth 285°, elevation 1.4°, diameter 0.53°; illustrative, not date-dependent |
| Sky | Vacuum black with a camera-visible solar disc; no atmospheric haze |
| Hardware | Terrain study; no official lander or base design |

The 2 m figure is grid posting, not an assertion of 2 m effective resolution or
vertical precision. DEM edges and invalid cells blend to available coarser grids.
The generated validation JSON records the loaded data and a sampled, curved
DEM-only solar horizon to 20 km. That check excludes small procedural occluders
and topography beyond the modeled region; it is not an illumination-duration
study. Small rocks, craterlets and grain are synthetic. Rock/crater abundance
has not been measured at this reference point.

The LROC Hapke parameter map bundled with the extension covers only 70° S–70° N.
This polar example deliberately uses the Apollo 17 analogue with neutral gray
appearance and the existing opposition shader, without claiming a polar
photometric calibration. Exposure is an artistic display choice.

## Rebuild

```sh
python3 tools/fetch_release_data.py
blender -b --python examples/moon_base.py
# Or Python 3.13 with the official bpy==5.2.1 wheel:
python examples/moon_base.py
```

`--draft` reduces rendering cost; `--reuse` retains the saved terrain. A complete
build renders both views and writes the Blender validation and SHA-256-pinned
scene catalogue under `build/moonbase/`. The scene embeds this document and its
data provenance.

## Gazebo

The matching Gazebo Harmonic ZIP contains the terrain, textured rocks, separate
collisions, lunar gravity, a surface camera and launcher. Extract the whole ZIP
and run `bash run.sh` from its `moonbase` directory. For headless use:
`bash run.sh -s --headless-rendering`.

Gazebo uses the exporter's **PBR approximation**. Hapke backscatter/opposition and
the Blender camera-visible solar disc do not transfer. This is static terrain,
not deformable soil or a mission dynamics model. See `EXPORT_GUIDE.md` and the
packaged validation logs; interactive GUI and ROS integration are not tested.

To export a newly built scene, use the Python 3.13 environment containing bpy:

```sh
python examples/moon_base_gazebo.py build
# In the Gazebo environment described in gazebo/environment.yml:
bash gazebo/tests/run_offline_tests.sh build/gazebo/moonbase
bash gazebo/test_server.sh build/gazebo/moonbase
python examples/moon_base_gazebo.py package
```

The package command requires successful actual Ogre2, DART and full Gazebo
server/camera checks. The dedicated workflow publishes only after those checks.

## Primary sources

- [NASA Blue Moon Mark 1 mission event](https://www.nasa.gov/event/clps-flight-blue-origins-blue-moon-mark-1/): target region and current schedule.
- [NASA Moon Base FAQ](https://www.nasa.gov/moon-base-frequently-asked-questions/): broader site selection remains under study.
- [NASA Lunar Surface Data Book, Rev A](https://ntrs.nasa.gov/citations/20230007818): Table A2-2, R01 reference coordinates (2023).
- [LROC NAC ESALL_CR1 product](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_ESALL_CR1): local stereo elevation data.
- [Bundled data provenance](lunar_terrain/data/PROVENANCE.md): elevation, photometry and analogue catalogue attribution.

This independent visualization is not a NASA or Blue Origin engineering model
and does not imply their endorsement.
