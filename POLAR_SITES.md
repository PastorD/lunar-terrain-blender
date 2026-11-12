# Lunar Atlas and polar presets — 1.6.0

Open [Lunar Atlas](https://github.com/PastorD/lunar-terrain-blender/releases/download/v1.6.0/Lunar_Atlas.html) locally in a browser. Eight locations have
real image references, Blender renders, source attribution and scene downloads.
The global map and south-polar inset select the same location cards. The HTML is
also bundled in **N → Lunar → Open Lunar Atlas**. Images require internet access.

Choose **Use this location**, then **N → Lunar → Import Location** in Blender.
Import the downloaded JSON and click **Build / Rebuild Lunar Terrain**. Only known
preset IDs are accepted; the importer does not execute code or arbitrary settings.

| New preset | Latitude | East longitude | Valid grid at origin | Reference |
|---|---:|---:|---:|---|
| Moon Base / Connecting Ridge | −89.46320° | 222.51000° | 2 m NAC stereo | NASA R01 |
| VIPER / Mons Mouton | −85.42088° | 31.62180° | 5 m adjusted LOLA | Published mission-area center |
| Nobile Rim 2 | −83.95400° | 58.82206° | 5 m adjusted LOLA | NASA DM2 |
| Malapert Massif | −85.99480° | 359.76422° | 4 m NAC stereo | NASA R23 |

These are **regional reference points, not confirmed touchdown coordinates,
landing ellipses or safe landing sites**. The original SOUTH preset retains its
nearby coordinate for compatibility. There are nine presets and eight atlas cards.

NASA's [VIPER mission page](https://science.nasa.gov/mission/viper/) and
[October 2026 rover update](https://www.nasa.gov/missions/moon-base/nasa-provides-progress-update-on-moon-base-rovers/)
identify Mons Mouton and delivery by Blue Moon Mark 1 in 2027. The coordinate is
the 5 × 4 km primary mission-area center published in
[VIPER Site Analysis](https://doi.org/10.3847/PSJ/ae061a), not a touchdown fix.

The other points come from the [2025 NASA Lunar Surface Data Book](https://ntrs.nasa.gov/citations/20250002845),
Table A2.1-1, printed page 75. Nobile Rim 2 and Malapert Massif appeared in NASA's
[October 2024 shortlist](https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/).
That historical candidate list does not imply final assignments under the later
mission architecture. Malapert Massif is distinct from the IM-1 landing site.
Connecting Ridge is an early Moon Base mission target region, not a finalized
permanent base site. Mission status checked **12 November 2026**.

## DEM and appearance scope

Native crops and 80 m averaged context come from
[GSFC adjusted LOLA grids](https://pgda.gsfc.nasa.gov/products/78), Site20, DM2 and
Site23, plus LROC NAC stereo where valid. The 3 m NAC footprint intersects the
VIPER origin but has a no-data gap there: **the actual loaded origin grid is 5 m**.
Surrounding valid NAC cells still contribute. Native MALAPERT02 supplies 4 m at
Malapert. LOLA provides wider context. Grid posting is not effective resolution;
5 m LOLA surfaces contain substantial interpolation between laser tracks.

Internal no-data edges now gradually blend into valid coarser data. The bicubic
stencil is guarded by two cells, with a sixteen-cell confidence ramp. No-data
holes are not filled with invented high-resolution elevations.

The three new Blender scenes cover a 20 km radius (40 km diameter), include lunar
curvature, continuous levels of geometry detail, craterlets and dust-coated,
fractured rocks. Sub-DEM features are procedural analogues, not mapped hazards.
All polar presets explicitly use an **Apollo 17 Hapke analogue** because the
regional parameter maps stop at 70°S. Sun angles are manual illustrations,
not date-dependent ephemerides. Ground and rock materials retain Hapke controls.

Unvisited polar regions use orbital photographs or mosaics in the report, never
claimed surface photographs. The images and renders do not have matched cameras.
Old Apollo and Chang'e released scenes preserve earlier appearance-study geometry;
rebuild them for the current 2 m / 4 m local grids. The report states that distinction.
Missing previews for Apollo surface, rock detail and the opposition test are
rendered from the checksum-pinned existing Blender files without rebuilding their
geometry. Existing Gazebo exports remain linked; no Gazebo validation is claimed for the
three new polar Blender examples.

## Reproduce

```sh
python tools/fetch_release_data.py
# Needed only with the older 1.5 data bundle:
python tools/prepare_polar_data.py
python tools/build_atlas.py --polar-map
python examples/polar_sites.py
python tools/package_release.py --output-dir dist/atlas
python tests/install_extension.py dist/atlas/lunar_terrain-1.6.0.zip
```

Use Python 3.13 with `bpy==5.2.1`, NumPy and Pillow for these build tools. The
installed extension needs only Blender's bundled Python/NumPy. Source image URLs
and credits are in `docs/atlas-data.json`. Source photographs remain hosted by
their publishers; their rights are not replaced by the repository's GPL license.
The polar map background is generated shaded relief from real DEMs, not a photo.
