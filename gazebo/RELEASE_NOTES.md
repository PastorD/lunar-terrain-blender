All seven Lunar Terrain examples are now available as self-contained Gazebo Harmonic worlds:

- Apollo 17 surface and concept outpost
- Chang'e-6
- Blue Ghost
- Chandrayaan-3
- Rock detail, including all three close-up rocks
- Opposition diagnostic, explicitly showing the limitation of stock PBR

Download a `*_Gazebo.zip`, extract the whole folder, then run `bash run.sh`.
Blender is not needed to use the Gazebo packages. Each includes SDF worlds,
textured COLLADA visuals, separate collisions, original camera/Sun direction,
lunar gravity, source metadata, launchers and validation evidence.

Every package passed actual Gazebo Common/Ogre2 rendering, DART contact and
lunar-gravity checks, and a full headless `gz sim` server/camera smoke test.
The PNG assets are actual Gazebo previews; validation JSON files identify the
source Blender checksums and build workflow. Interactive GUI and ROS bridge
operation are not covered.

**Materials are PBR approximations. Hapke opposition/backscatter, Blender color
management and fine Cycles shadow fidelity are not retained.** Both diagnostic
panels are intentionally identical in Gazebo. The original `.blend` files in
[v1.5.0](https://github.com/PastorD/lunar-terrain-blender/releases/tag/v1.5.0)
retain the Hapke shader. The saved DEM geometry is preserved rather than rebuilt.
Outpost hardware is static, without rover dynamics or a soil-traction model.

See the [Gazebo guide](https://github.com/PastorD/lunar-terrain-blender/tree/main/gazebo)
for each scene's extent, source data, testing and rebuild instructions.
`Lunar_Terrain_Gazebo_Exporter.zip` contains the source; `SHA256SUMS` covers all assets.
