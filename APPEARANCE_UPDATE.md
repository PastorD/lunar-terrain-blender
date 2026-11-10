# Apollo and Chang’e appearance update — 1.1

Install `Lunar_Terrain-1.2.0.zip` in Blender 5.2 or newer. The regional photometric parameters introduced in version 1.1 are retained; see `BLENDER_52_UPDATE.md` for the Blender and rock-detail update. In **N → Lunar → Sun and Hapke opposition**, choose **Apollo references** or **Chang’e references**, then **Apply Reference Appearance**. This also upgrades the version 1.0 generated materials. It updates existing terrain without rebuilding geometry or moving the camera or Sun. After manual edits, use **Update Lighting and Materials**.

The Apollo look is brighter and neutral gray. The Chang’e look is darker with a restrained warm tint. Broad cool soil mottling and exaggerated bump pits are reduced; fine fragments, crater geometry and real DEM elevations are retained. These are appearance matches to the supplied processed photographs, not calibrated photometric inversions or reproductions of their exact camera positions. The different Chang’e frames also have different exposures; the Exposure control lets you match an individual frame.

| Setting | Apollo references | Chang’e references |
| --- | ---: | ---: |
| Single-scattering albedo w | 0.19069648 | 0.21589789 |
| Two-lobe HG b | 0.26402950 | 0.26576930 |
| Two-lobe HG c | 0.07014839 | 0.05458565 |
| Shadow-hiding amplitude | 2.18679166 | 2.11557031 |
| Shadow-hiding width h | 0.07088306 | 0.04320762 |
| Photometric roughness | 23.656601° | 23.656601° |
| Coherent-backscatter amplitude | 0 | 0 |
| Porosity correction K | 1 | 1 |
| Exposure, stops | +4.4 | +2.8 |
| Linear RGB appearance tint | 0.95, 0.95, 0.95 | 1.00, 0.90, 0.74 |
| Soil tint endpoint variation | ±10% | ±8% |
| Dust-coated rock / soil w | 1.08 | 1.08 |

The photometric values come from the actual **WAC_HAPKEPARAMMAP_566NM v1.1** cells covering Apollo 17 and Chang’e-6. They are 1° regional, single-band priors, not measurements of the individual stones or a determination of which Chang’e mission acquired the supplied photos. The exposure and RGB controls are artistic adjustments. See the [LROC parameter product](https://data.lroc.im-ldi.com/lroc/view_rdr/WAC_HAPKEPARAMMAP) and [Sato et al. (2014), Appendix A](https://doi.org/10.1002/2013JE004580).

The implementation now uses two-lobe Henyey–Greenstein scattering, the logarithmic H-function approximation, effective incidence/emergence angles and the Hapke roughness shadowing correction. Positive c increases the backward lobe, with weight (1+c)/2; c is in [-1,1]. Width h is a dimensionless tangent half-angle parameter, not degrees. Roughness is an unresolved-slope parameter, separate from mesh displacement.

The published parameter variant fixes K=1 and CBOE amplitude=0: its fitted shadow-hiding term already absorbs the unresolved opposition surge. An additional coherent-backscatter peak is therefore disabled by default. Advanced CBOE controls remain available for independently fitted values; its inactive default h is 1. The product's roughness value is 23.656601°, slightly different from the rounded 23.4° reported in the paper.

**Use LROC Parameters at Location** reads the bundled 566 nm parameter map while retaining exposure and color. Coverage is 70°S–70°N; outside it, the operator reports missing coverage and retains the current values. Cells outside the supported parameter range are also rejected without changing existing values. Polar terrain can use a selected reference appearance as an explicit analogue. It is not assigned a fabricated polar fit.

Use AgX / Medium High Contrast and the scene's Sun strength 3.8 for the example appearances. The physical solar angular diameter remains 0.53°. The sky is black, cast shadows remain ray traced, and the camera-visible Sun still follows the light. No ground emission or ambient fill is introduced.

This remains a native-node, direct-Sun approximation using a view-dependent Diffuse BSDF weight. It is not a general multi-light Hapke closure. Indirect-light angular response and angular integration across the solar disc remain approximate. Orbital-fit accuracy at very grazing surface-view angles is not established by the implementation tests.

`examples/Apollo17_Surface.blend` and `Apollo17_Outpost.blend` retain their original DEM geometry and cameras with upgraded materials. `ChangE6_Surface.blend` demonstrates the warm appearance at the Chang’e-6 coordinate using real, lower-resolution LOLA context; sub-DEM relief and rocks remain synthetic. All example scenes use native Blender data and reopen without installing the add-on. The add-on is required to regenerate terrain.
