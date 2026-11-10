# Chandrayaan-3 preset — Lunar Terrain 1.5.0

Select **Chandrayaan-3 / Shiv Shakti** in **Lunar → Location preset**, click **Apply location and look**, then **Build / Rebuild Lunar Terrain**. The native crop works offline. **Chandrayaan-3 photo references** opens the linked catalogue. For an existing scene, choose **Chandrayaan-3 / Pragyan NavCam** under **Reference appearance** and apply it; this preserves the geometry, camera and Sun.

## Reference photographs

The principal targets are ISRO's rover views of Vikram from **30 August 2023, 07:35 and 11:04 IST**. The latter was photographed from approximately 15 m. The catalogue distinguishes annotated duplicates, stereo composites and a distant lander view in the [2024 research update](https://www.isro.gov.in/ch3_Discovery_of_a_buried_crater_on_the_moon.html). It also links additional processed stereo views in Figures 2 and 3 of [Relia et al. (2026)](https://arxiv.org/pdf/2603.26802#page=2), and supporting tracks, crater, touchdown, deployment and hop photographs.

There are **six direct lander-reference image assets, two further paper figures, and seven supporting surface image assets**. These are not fifteen independent lander viewpoints. All relevant still assets identified in the reviewed [ISRO gallery](https://www.isro.gov.in/chandrayaan3_gallery.html), research releases and paper/Commons variants are catalogued. **Every raw mission frame is not claimed**: the larger [PRADAN archive](https://pradan.issdc.gov.in/ch3/) requires registration and was not exhaustively enumerated. Its [FAQ](https://pradan.issdc.gov.in/ch3/faq.xhtml) explains raw/calibrated NavCam PNG/XML and LI/RI JPG/XML downloads. Original links, groups and checksums are in `lunar_terrain/data/Chandrayaan3_References.json`; the HTML catalogue loads previews from ISRO. Photographs are not bundled or relicensed as GPL.

## Surface appearance

The target is neutral grayscale: medium-gray soil, hard shadows, granular relief, sparse fragments and a low rolling horizon. Red/cyan anaglyph colours encode stereo, not regolith colour. Existing fractured rock geometry and metric grain are retained. ISRO's traverse study reports no boulders larger than 1 m along the reported path; it does not supply a complete small-rock size distribution.

These controls are **visual choices**, not measured population or camera fits:

| Control | Value |
| --- | ---: |
| Rock projected area | 0.07% |
| Crater analogue multiplier / depth multiplier | 0.35 / 0.60 |
| Fine fragments | 12/m² |
| Small craterlets | 0.65/m² |
| Fine ground relief / soil texture relief | 2.0 / 2.2 |
| Camera height / lens / pitch | 0.65 m / 51 mm / −6° |
| Camera heading | 90° |
| Sun azimuth / elevation / diameter | 355° / 18° / 0.53° |
| Sun strength / exposure | 3.8 / 1.8 stops |
| Neutral soil balance / albedo variation | (0.92, 0.92, 0.92) / 0.06 |
| Rock/soil albedo ratio | 1.04 |

A 51 mm lens on the virtual 36 mm sensor gives about 38.9° horizontal field of view, close to the 39° NavCam field reported by Relia et al. The height and pose remain illustrative. Lighting is art-directed, without a date-based ephemeris. A seed controls synthetic stones and pits; the DEM cannot locate centimetre features from the photographs. A Vikram lander model, exact lander shadow, rover tracks and plume-disturbed patch are not included: this is a terrain/material study.

## Real DEM and corrected coordinates

The preset uses **69.373° S, 32.319° E**, printed on ISRO's annotated image. [LROC](https://lroc.im-ldi.com/images/1314) reports 69.3741° S, 32.32° E, about 35 m away; use the coordinate fields when exact photo registration matters.

The bundled [LROC NAC VIKRAMSITE1](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_VIKRAMSITE1) crop has **3 m native grid spacing**, about 4.4 km across, with pre-landing topography. **LOLA LDEM_64, 473.8 m nominal grid**, supplies distant context. Missing cells and edges blend into fallback data. The panel reports actual loaded data. A 0.12 m mesh supplies procedural sub-DEM relief, not measured decimetre topography. Grid spacing is not effective resolving power.

A [February 2026 OHRC stereo preprint](https://arxiv.org/abs/2602.14993) reports a 0.303 m derived DEM, but its data statement says derived products will be archived upon acceptance. A downloadable elevation raster was not verified, so this release uses the verified 3 m public product and does not advertise the preprint spacing as loaded data.

This site exposed a projection bug: PDS Polar Stereographic `CENTER_LATITUDE` is a latitude of true scale. VIKRAMSITE1 uses −69.3°, not −90°. Version 1.5 applies spherical scale `(1 + sin(abs(latitude_ts))) / 2` in forward/inverse transforms and the coverage-map raster check. Ignoring it displaced sampling about 20 km. Pole-scale products retain their previous transforms. Independent PROJ checks and valid native cells at the origin verify the correction; origin elevation is approximately 532.50 m.

## Hapke photometry

The regional 1° LROC WAC 566 nm cell supplies the physical prior, not an inversion of processed NavCam photographs:

| Parameter | Value |
| --- | ---: |
| Single-scattering albedo w | 0.42367154 |
| Two-lobe width b | 0.18872121 |
| Backward balance c | 0.86234498 |
| SHOE amplitude B_SH0 | 1.52612853 |
| SHOE width h_SH | 0.01366348 |
| Photometric roughness | 23.656601° |
| CBOE amplitude | 0 |

Opposition strength remains 1; CBOE stays off to avoid a second surge on top of the fitted term. Exposure, colour and soil bump gain are independent appearance controls. The existing single-Sun view-dependent Diffuse-BSDF approximation retains real Cycles shadows; indirect or multiple-light response is approximate. See APPEARANCE_UPDATE.md.

## Reproduce and install

`examples/chandrayaan3.py` builds `examples/Chandrayaan3_Surface.blend` and its Cycles PNG: 20 km terrain radius, 24 m near detail, 0.12 m mesh spacing, 1024² pixels and 64 samples. `--draft` uses 768²/24; `--reuse` reopens the scene and reapplies appearance. Run using Blender background Python or the official bpy module.

The extension ID remains `lunar_terrain`; new enum identifiers are appended so previous selections retain their meaning. The restricted-registration fix remains. Tests cover the actual installable ZIP, all five locations offline, disable/re-enable, and an update from 1.4.0 preserving settings and cache. Runtime scope: official Linux bpy 5.2.1, headless CPU; no interactive UI or GPU validation is claimed.
