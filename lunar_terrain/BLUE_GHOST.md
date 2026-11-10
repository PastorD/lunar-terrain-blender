# Blue Ghost reference preset — Lunar Terrain 1.4.0

Choose **Blue Ghost 1 / Mare Crisium** under **Location preset**, then click **Apply location and look** and **Build / Rebuild Lunar Terrain**. For an existing scene, choose **Blue Ghost references** under **Sun and Hapke opposition → Reference appearance**, then click **Apply Reference Appearance**. The appearance-only action preserves terrain, rocks, the camera and Sun direction.

The supplied images guide the cool gray highlights, deep shadows, sparse fragments and granular soil. The location preset uses a 2.5° Sun behind a west-facing, 20 mm camera at 2 m height. This places the view near the shadow/opposition direction. The camera-visible Sun remains on the opposite side of the sky; the small bright disc in the second supplied image is Earth.

## Physical data and appearance

The location is **18.5623° N, 61.8103° E**, from the [LROC landing-site observation](https://lroc.im-ldi.com/images/1407). A bundled native crop of [LROC CRISHORSE01](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_CRISHORSE01) supplies **3 m grid spacing** near the landing site. Its crop spans about 4.4 km, with missing cells and edges handled by the existing fallback blending. Bundled SLDEM2015 context supplies about **59.225 m** spacing farther out. The panel reports actual loaded data; a finer mesh adds procedural relief below those measured grids.

The 1° LROC WAC 566 nm cell at the site supplies the same model variant used by Apollo and Chang'e:

| Parameter | Value |
| --- | ---: |
| Single-scattering albedo w | 0.19665816 |
| Two-lobe width b | 0.25865856 |
| Backward balance c | 0.11911466 |
| Shadow-hiding amplitude B_SH0 | 2.12918901 |
| Shadow-hiding width h_SH | 0.06456485 |
| Photometric roughness | 23.656601° |
| Coherent-backscatter amplitude | 0 |

The preset keeps the regional opposition fit; it does not add a second coherent-backscatter surge. The existing single-Sun Hapke approximation and its limitations remain documented in APPEARANCE_UPDATE.md.

Exposure and soil colour balance are independent artistic controls. They approximate the supplied processed photographs; they are not a radiometric calibration or a claim that mare soil is intrinsically blue. Rock area **0.12%**, crater abundance **0.65**, depth multiplier **0.85**, ten fine fragments/m² and 0.5 small craterlets/m² are visual choices using the existing surface analogue, not measured Blue Ghost population estimates.

The two references differ in colour and shadow coverage. The default favours the second, cooler image. For the warmer late-light photograph, try setting the Sun to 1–2°, moving Sun azimuth to 270° and camera heading to 90°, and bringing **Soil color balance** toward neutral/slightly warm. These are art-directed views, not recovered mission timestamps.

[Firefly’s mission images and captions](https://fireflyspace.com/news/blue-ghost-mission-1-live-updates/) distinguish early surface imagery from the later sunset observations. This preset recreates terrain appearance. A Blue Ghost lander model, its exact shadow, Earth imagery and a mission ephemeris are not included.

## Example and compatibility

The complete project includes **examples/BlueGhost_Surface.blend**, a CPU Cycles render and **examples/blue_ghost.py** to rebuild it. The study uses a 20 km terrain radius, 24 m near-detail radius and 0.12 m near mesh spacing.

The preset is appended to the existing choices so saved Apollo, south-pole and Chang'e selections retain their identifiers. Changing a location preset now resets camera height/lens to that location's reference framing; appearance-only changes preserve both. The extension retains the 1.3.2 manifest and restricted-registration fixes.
