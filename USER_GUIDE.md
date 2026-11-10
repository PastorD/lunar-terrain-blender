# Lunar Terrain 1.5.0

A Blender 5.2+ extension for choosing a lunar latitude and longitude, sampling real elevation data, and building continuous terrain with progressively coarser geometry toward the horizon. It adds angular rocks, degraded craters, granular regolith, Sun-linked Hapke opposition shading, and an optional editable rover and moon base.

The supplied Blue Ghost photos guide a separate cool, low-Sun reference appearance. The Apollo 17 reference supplied with the request guided the brighter gray soil, embedded fragments, shallow worn pits and restrained fine relief. This is an interpretation of its surface appearance, not a reconstruction of the photograph's camera position. The two example scenes use real Taurus–Littrow elevation data. A separate south-pole preset uses actual adjusted LOLA terrain and grazing illumination.

Version 1.3 adds native DEM selection, an offline coverage map and actual loaded-grid reporting. See [DEM_UPDATE.md](DEM_UPDATE.md). Version 1.2 introduced Blender 5.2 support and close-up rock detail. See [BLENDER_52_UPDATE.md](BLENDER_52_UPDATE.md) for upgrading and reproducing the checks.

Version 1.1 introduced separate Apollo and Chang’e appearances, actual regional LROC photometric priors, two-lobe scattering and a Hapke roughness correction. See [APPEARANCE_UPDATE.md](APPEARANCE_UPDATE.md) for parameters and upgrading existing scenes.

Version **1.3.1** fixes the `_RestrictData.scenes` registration error in Blender 5.2.1. Restart Blender after a failed 1.3.0 enable, then install the new ZIP. See [INSTALLATION_FIX.md](INSTALLATION_FIX.md).

Version **1.3.2** corrects extension-manifest validation and uses Blender’s official extension build tools. See [EXTENSION_INSTALL.md](EXTENSION_INSTALL.md) for installation and updating.

Version **1.4.0** adds **Blue Ghost 1 / Mare Crisium** and a **Blue Ghost references** appearance. It bundles a local 3 m LROC grid and wider SLDEM2015 context. See [BLUE_GHOST.md](BLUE_GHOST.md) for colour, illumination, parameters and the rendered study.

Version **1.5.0** adds **Chandrayaan-3 / Shiv Shakti**, a neutral **Pragyan NavCam** appearance, a linked public-photo catalogue, native 3 m terrain, and **Soil texture relief**. It corrects polar true-scale latitude handling. See [CHANDRAYAAN3.md](CHANDRAYAAN3.md).

## Install and use

1. Use Blender **5.2 or newer** (tested in 5.2.1 LTS). Open **Edit → Preferences → Get Extensions**, open its menu, and choose **Install from Disk**. Select `lunar_terrain-1.5.0.zip` and enable Lunar Terrain.
2. Start with an empty scene for a clean view. In the 3D View, press **N** and open the **Lunar** tab.
3. Choose a preset and click **Apply location and look**, or enter planetocentric latitude and east-positive longitude. Negative west longitudes are accepted.
4. Set terrain radius, near detail radius and near mesh spacing. Click **Build / Rebuild Lunar Terrain**. Press **F12** to render.
5. Enable **Add concept rover and moon base** before building for the outpost. Change Sun controls and click **Update Lighting and Materials** to avoid rebuilding geometry.

The add-on needs only Blender's bundled Python and NumPy. No pip installation is needed for normal use. The optional GeoTIFF converter is an external Python tool with separate dependencies.

Rebuilding replaces objects tagged by this add-on. Existing user objects are retained, including user objects placed inside a generated collection. **Clear Generated Terrain** restores the original camera/world pointers when they were replaced. Render settings and unit settings are not automatically restored. Existing cubes or lights may affect the result; the add-on does not delete them.

The panel operates on Blender's main thread in stages. **Esc** cancels between stages or download strips; a large geometry stage can take several seconds. A failed or cancelled generation retains the last completed terrain. A memory or instance budget error asks for reduced detail instead of silently reducing the specified population.

## Locations and measured resolution

| Preset | Native local DEM | Distant / fallback data |
| --- | --- | --- |
| Apollo 17 | LROC NAC 2 m, bundled native crop | SLDEM2015 59.225 m |
| Chang’e-6 | LROC NAC 4 m, bundled native crop | LOLA 473.8 m and 1895 m offline; finer context downloads available |
| Connecting Ridge | LROC NAC 2 m where valid | Adjusted LOLA 5 m and 80 m context |
| Blue Ghost 1 | LROC NAC CRISHORSE01 3 m, bundled native crop | SLDEM2015 59.225 m |
| Chandrayaan-3 | LROC NAC VIKRAMSITE1 3 m, bundled native crop | LOLA 473.8 m context |
| Other coordinates | Smallest grid in supported catalog, downloaded near focus | Global LOLA offline fallback |

The **DEM and spatial resolution** panel distinguishes available catalog grid, actual loaded cells and procedural mesh spacing. **Native DEM radius** defaults to 2 km; terrain radius defaults to 20 km. Grid spacing is not effective resolving power. The 687 local footprints can contain missing pixels; JAXA SLDEM2013 supplies a nominal 7.403 m global grid with coarser effective detail. See [DEM_UPDATE.md](DEM_UPDATE.md) for map scope, transfer budget, native readers, coordinate frames and curvature limits.

New settings download finer data before building when Blender’s **Allow Online Access** is enabled. Offline builds use bundled and cached data and report it. Use **Open DEM Coverage Map** to query coordinates and **Show DEM Source Report** to inspect actual source weights and download errors. A 0.10 m mesh adds procedural detail below the DEM, not measured decimetre terrain.

## Continuous spatial resolution

The surface is one connected mesh with shared vertices and smooth normals. Concentric rings become gradually coarser with distance, and unequal rings are triangulated together. There are no overlapping square terrain tiles. All elevations and procedural relief use the same continuous local coordinates; DEM edges blend into coarser data, and textures are not reset per patch.

The terrain radius is measured around the detail focus. **Automatic** places near detail below the generated surface camera or outpost camera. **Location origin** keeps detail at the chosen location. **Active camera** retains the current perspective camera's world transform and lens and moves the detailed terrain below it. Move your camera and rebuild when exploring elsewhere: this is a static mesh, not a continuously retessellating viewport system. Active-camera focus is limited to 50 km from the location origin.

Local units are metres: **+X east, +Y north, +Z up**, relative to the DEM elevation at the selected location. Geodesy uses a 1,737,400 m lunar sphere and includes lunar curvature by default. This is terrain visualization, not a navigation or landing certification product.

## Rocks and crater populations

The starting analogue is the Chang'e-6 surface catalogue released with Zhao et al. (2025). The included CSV retains 435 crater records whose centres fall within an interior 40 × 40 m window. The 434 records with diameters from 0.52 to less than 10 m supply the generated size distribution; valid depth/diameter ratios are resampled separately. Positions, orientations, worn rims and shapes are generated from the seed. Density is multiplied by **Crater abundance**. Sparse large craters and far mountain morphology come from the DEM; the add-on does not claim to reproduce catalogue crater positions at an arbitrary location.

For rocks, the cumulative projected-area analogue is

`F(>D) = k exp(-β D)`, with `β = 0.5648 + 0.01258/k`,

where D is in metres and k is a fraction. The sampler converts area abundance into differential number density using equivalent projected rock area: `n(D) = 4 k β exp(-β D)/(π D²)`. The panel displays k in percent. The Chang'e-6 starting value is **0.179%**; the Apollo appearance preset's **1%** is an artistic adjustment, not a measured Apollo 17 population. The exponential law is an approximation with published residuals, not a universal lunar distribution. Polar abundance varies with terrain and ejecta setting.

Twenty-four fractured rock prototypes are instanced efficiently. Nearby rocks at least 0.15 m across use 2,562 vertices and 5,120 triangles per prototype, with chipped surfaces and broken stress fractures; small or distant rocks use 42 vertices and 80 triangles. Fine pits, metric grain and subdued mineral mottling enrich the rock material. Use **Upgrade Rock Detail** to update rocks in an existing scene. Prototypes are normalized by their projected convex-hull area and partially embedded in the surface. Fine fragments (5–25 mm) and small craterlets (0.20–0.52 m) have separate **artist-authored** controls because the cited crater catalogue does not establish their completeness. Both can be set to zero. Their near-camera concentration is a rendering choice, not a geological discontinuity in the measured DEM.

Recent work on submetre lunar impact modification informs the restrained, degraded surface treatment. It does not supply a measured rock density for every selectable site. The exact local geology cannot be inferred from a DEM alone.

## Hapke lighting and visible Sun

The native node group now uses a two-lobe Henyey–Greenstein phase function, logarithmic H-functions, effective angles, and a Hapke photometric roughness correction. The default Apollo and Chang’e parameter sets use actual LROC 566 nm regional fits with K=1 and CBOE amplitude=0. The fitted shadow-hiding term absorbs the unresolved opposition surge. Exposure and soil color are independent appearance controls; see [APPEARANCE_UPDATE.md](APPEARANCE_UPDATE.md) for the full table and conventions.

This is a **single-Sun direct-light approximation implemented as a view-dependent Diffuse BSDF weight**. Actual Cycles shadows remain intact. It is not a general custom path-tracer BRDF: angular behavior under multiple lights or indirect illumination is approximate. The finite Sun controls shadow softness, but its angular integration through the Hapke weight uses the disc centre. The appearances are not calibrated inversions of the supplied processed photographs.

**Yes, the Sun is visible when a camera looks at it.** A camera-visible world disc follows the actual Sun direction and diameter, while the Sun light supplies illumination and shadow softness. Select **Lunar • look at Sun** as the active camera to inspect it. It is occluded by intervening geometry, and the world stays black away from the disc. The disc's brightness is a display value, not calibrated solar radiance. The opposition brightening appears when the Sun is **behind the observer**, near the observer's shadow; it is a different viewing direction from looking at the Sun.

Default solar diameter is 0.53°. The Apollo appearance study uses 18° Sun elevation and an art-directed exposure; these are not the Apollo photograph's recovered ephemeris. The south-pole preset uses 1.7°. Location changes do not compute date-dependent illumination.

## Example scenes and source

`examples/Chandrayaan3_Surface.blend` is the 1.5 neutral NavCam terrain study. `examples/BlueGhost_Surface.blend` is the 1.4 study; its render is generated by Cycles from the included scene. The earlier `.blend` files retain the 1.2 appearance studies. Rebuild their terrain in 1.3 to use the new native DEMs; their stored renders have not been replaced.

`examples/Apollo17_Surface.blend` is the terrain study. `examples/Apollo17_Outpost.blend` adds the editable concept rover, habitats, solar panels and astronaut. `examples/ChangE6_Surface.blend` is an additional warm ground study. All three reopen and render without installing the add-on; the add-on is required to regenerate their terrain. All shader nodes and rock geometry are native Blender data. The rover is a simplified original concept inspired by the Toyota/JAXA reference, not an official engineering model.

`examples/Rock_Detail.blend` shows the generated material and three staged rocks at close range.

Run `examples/build_examples.py` using Blender's background Python mode to rebuild both examples. `tests/integration.py` exercises geodesy, mesh continuity, operator lifecycle, cancellation, object preservation and the camera-visible solar disc. `VALIDATION.md` records the delivered build's actual checks.

To use an external lunar GeoTIFF:

```sh
python -m pip install numpy rasterio
python tools/convert_dem.py input.tif local_dem.npz
```

The converter accepts north-up lunar geographic, simple cylindrical and pole-centred stereographic grids on the same lunar sphere. Use `--window COL ROW WIDTH HEIGHT` for a crop or `--vertical-scale 1000` for kilometre elevations. Invalid/no-data pixels fall back to coarser bundled data. Unsupported Earth datums, rotated grids and incompatible projections are rejected. Select the resulting file in **Extra DEM pack**.

## Sources and attribution

- NASA/MIT [LOLA PDS cylindrical products](https://imbrium.mit.edu/DATA/LOLA_GDR/CYLINDRICAL/IMG/) and accompanying labels; global integer elevations are multiplied by **0.5 m**.
- NASA [SLDEM2015 product description](https://pgda.gsfc.nasa.gov/products/54), Barker et al. (2016), [doi:10.1016/j.icarus.2015.07.039](https://doi.org/10.1016/j.icarus.2015.07.039). Original float elevations in **kilometres** are converted to metres.
- NASA adjusted [Site01 5 m DEM](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_surf.tif) and [80 m south-pole DEM](https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF); float elevations are already metres.
- Zhao et al. (2025), [doi:10.1029/2025JE008960](https://doi.org/10.1029/2025JE008960); derived catalogue from [Zenodo 14920942](https://doi.org/10.5281/zenodo.14920942), **CC BY 4.0**. Window selection and field conversion are documented in `data/surface_reference.json`.
- Yan et al. (2025), [doi:10.1038/s41467-025-59443-5](https://www.nature.com/articles/s41467-025-59443-5), including the supplementary rock-area model and coordinate comparison.
- Liu et al. (2026), [doi:10.1038/s43247-026-03270-z](https://doi.org/10.1038/s43247-026-03270-z), submetre impacts and surface modification context; not a site density calibration.
- Kawashima et al. (2022), [LPSC 1312](https://www.hou.usra.edu/meetings/lpsc2022/pdf/1312.pdf), polar rock-population variability.
- [USGS ISIS Hapke documentation](https://isis.astrogeology.usgs.gov/8.1.0/Object/Programmer/class_isis_1_1_hapke.html), photometric model reference.
- [Toyota/JAXA Lunar Cruiser reference, 31 March 2025](https://global.toyota/en/mobility/technology/lunarcruiser/20250331.html).

Source code is GPL-3.0-or-later; see `lunar_terrain/LICENSE`. Derived Chang'e-6 catalogue data remain CC BY 4.0 with the attribution above. NASA elevation products retain their source attribution. No publisher figures or mission photographs are redistributed. Pack metadata and checksums are in `lunar_terrain/data/provenance.json`.
