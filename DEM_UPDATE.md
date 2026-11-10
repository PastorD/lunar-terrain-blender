# Lunar Terrain 1.3 — native DEM selection

Version 1.3 selects the finest **published grid in its supported public catalogs** at the requested location. It reports catalog availability separately from elevations actually loaded. It targets Blender 5.2, with validation in the official Linux Blender 5.2.1 Python module.

The **1.3.1 patch** fixes Blender’s restricted registration error without changing the native DEM implementation; see [INSTALLATION_FIX.md](INSTALLATION_FIX.md).

## What changed

| Preset | Previous local grid | New bundled native grid | Product |
| --- | ---: | ---: | --- |
| Apollo 17, 20.1908° N, 30.7717° E | 59.225 m | 2 m | [LROC NAC APOLLO17_2M](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_APOLLO17_2M) |
| Chang’e-6, 41.6385° S, 206.0148° E | 473.8 m context | 4 m | [LROC NAC CHANGE6](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_CHANGE6) |
| Connecting Ridge, 89.438788° S, 222.844980° E | 5 m | 2 m where valid; 5 m fallback | [LROC NAC ESALL_CR1](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_ESALL_CR1) |

The native crops were requested at 2.2 km radius, with interpolation padding, and clipped to source bounds. They keep the original cells; there is no elevation upsampling in the downloaded packs. Their valid coverage is not a perfect disk, especially at the south pole. Existing coarser DEMs provide distant terrain and fill missing pixels.

## Using the panel

1. Install `Lunar_Terrain-1.3.1.zip` from Blender’s **Preferences → Get Extensions → Install from Disk**, then enable Lunar Terrain. The complete project ZIP is for source and examples, not installation.
2. Enter planetocentric latitude and east longitude in **3D View → N → Lunar**. Apply a preset if desired.
3. **DEM and spatial resolution** shows the smallest catalog grid and source name immediately. Open the offline coverage map to inspect any coordinate and its overlapping products.
4. **Download finer DEM before building** defaults on for new settings. Enable Blender’s **Allow Online Access** for downloading. Offline builds use bundled/cache data and say so.
5. Set **Native DEM radius** (default 2 km) around the detail focus, and a transfer budget (default 1024 MiB). Distant terrain uses coarser context. Increase native radius when moving beyond the downloaded area.
6. **Build / Rebuild** replaces the add-on’s generated terrain. **Inspect Cached DEM Resolution** checks source cells without rebuilding. **Show DEM Source Report** opens a Blender text block containing sources, effective centre weights, focus coordinates, perimeter grid samples, and download errors.

An available catalog entry is not labelled as loaded until valid cells are sampled. If a download fails or the budget is exhausted, available fallback elevations remain usable and the operation reports partial completion. A cancelled build retains the previous generated scene. Completed cache packs are reused. Changing location clears stale reports.

The report samples the origin, detail focus and 24 points around the terrain perimeter. Those samples describe the selected locations; they are not a guarantee that the entire interior uses one grid. The procedural mesh spacing remains a separate control: a 0.10 m mesh does not imply measured 0.10 m topography.

## Map scope and effective resolution

`Lunar_DEM_Map.html` includes coordinate lookup and source links; `Lunar_DEM_Map.png` is a printable figure. Both use the same catalog as the add-on. It contains **660 LROC NAC stereo footprints** released through 2026-06-15 and **27 NASA adjusted LOLA polar products**, with JAXA SLDEM2013 as the global nominal grid baseline.

There is no uniform “highest resolution for the Moon.” [JAXA SLDEM2013](https://darts.isas.jaxa.jp/en/datasets/darts:sln-l-tc-5-sldem2013-v1.0/) has 4096 pixels per degree, about 7.403 m north–south on the 1737.4 km sphere. Its principal TC input is about 10 m; smoothing, resampling and MI/LOLA fill make effective detail coarser and variable. East–west spacing of a geographic grid also contracts with latitude. [NASA’s 5 m polar grids](https://pgda.gsfc.nasa.gov/products/78) interpolate extensively between laser measurements. LROC stereo grids likewise have product-specific matching and vertical errors. The UI deliberately calls these values **grid spacing**.

The map is not an exhaustive inventory of isolated research, lander/rover photogrammetry or unpublished DEMs. [USGS Kaguya TC v2](https://stac.astrogeology.usgs.gov/docs/data/moon/kaguyatc_dtms/) offers newer calibration and registration, generally with coarser grids than the nominal SLDEM2013 baseline; [NASA polar shape-from-shading DEMs](https://pgda.gsfc.nasa.gov/products/104) offer another local quality option. They are documented alternatives rather than automatic sources in 1.3. A smaller grid does not necessarily have better vertical accuracy or geodetic control. Use the supplied converter and **Extra DEM pack** for another compatible source.

## Download and blending details

Native readers need only Blender’s NumPy and standard Python. LROC PDS labels supply the sample type, scaling, attached-image byte offset, projection, pixel-centre convention and native spacing. Geographic, equirectangular and unit-scale lunar polar stereographic grids are supported. NASA GeoTIFF/BigTIFF readers accept north-up single-band elevation, raw/Deflate compression and predictors 1/2/3; unsupported TIFF encodings can be converted outside Blender using Rasterio.

LROC’s `.PYR.TIF` browse images are not elevation and are never used as DEMs. Downloads normally require verified HTTP byte ranges. The exception is JAXA’s label-verified 4096×4096 int16 tile: when the server ignores ranges, exactly 32 MiB may be downloaded, only within the remaining budget. No arbitrary full-file fallback is allowed. Source URLs and native row/column windows are retained in pack metadata.

Native crops are split into overlapping windows of at most 4096×4096 cells. Shared cells retain the same coordinates and elevations; a 16-cell smooth edge blend prevents square crop boundaries from becoming sharp seams. The elevation cache is lazy and bounded to roughly 384 MiB; source decompression buffers have separate bounds. Total scene memory also depends on mesh and rock settings. NoData uses coarser elevations. Different instruments and registrations can still disagree in height; this is a visualization mosaic, not a new geodetically adjusted research DEM.

## Extent and lunar curvature

The terrain radius defaults to **20 km** and the existing control allows **50 km**. The curvature calculation uses the lunar radius 1,737,400 m and the local elevation. At an eye height of 1.65 m, the ideal smooth-sphere horizon is about **2.39 km**. An elevated mountain can be visible beyond it: approximately **21.0 km** for a 100 m summit, **44.1 km** for 500 m, **61.3 km** for 1 km, and **85.8 km** for 2 km, using the sum of observer and summit horizon distances. Intervening relief can occlude these views.

Thus a 20 km mesh covers local horizons but does not include every geometrically visible tall mountain; even the current 50 km cap cannot include all 1–2 km summits. Increasing DEM resolution does not extend the mesh. This release retains the existing extent controls and reports the actual grids at that extent. The test builds also check finite elevations along ±20 km transects. The scientific approximation is `d ≈ sqrt(2Rh_observer) + sqrt(2Rh_summit)`; curvature drop below the local tangent plane is approximately 115 m at 20 km and 720 m at 50 km.

## Existing scenes and validation

Existing `.blend` examples preserve the earlier appearance and rock-detail studies. They are **not newly rendered 1.3 DEM examples**. Install 1.3 and click **Build / Rebuild** to replace their terrain with the new data. Hapke parameters, fractured large-rock geometry, textures, crater population models and visible-Sun behavior are retained.

Reproducible checks are included in `tests/native_dem.py`, `tests/blender_dem_upgrade.py` and `tests/install_extension.py`. Their JSON records document independent Rasterio/GDAL comparisons of original PDS/BigTIFF bytes, overlap seams, NoData, longitude/pole handling, transfer bounds, native builds and installation of the delivered ZIP. Testing is headless Linux CPU in the official Blender 5.2.1 module; it does not establish interactive Blender UI or GPU compatibility on every platform. The offline map has a separate browser validation record.

Catalog refresh is a development operation using `tools/build_dem_catalog.py` (requires pyshp and Shapely), followed by `tools/make_dem_map.py` (Matplotlib). Normal add-on use requires neither library. Public product availability can change after the catalog snapshot.
