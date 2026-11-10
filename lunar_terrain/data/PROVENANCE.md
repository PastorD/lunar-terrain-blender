# Elevation pack provenance

The NPZ packs retain native elevation samples with no raster resampling. Global LOLA stores source int16 values with scale 0.5 metres. The Apollo SLDEM float crop has already been multiplied from kilometres to metres and uses scale 1. Polar crops retain float elevations in metres. Metadata west/north refer to pixel edges; sampling uses pixel centres. Source rows/columns are zero-based, end-exclusive.

The 80 m source hash is for the intermediate 100 km cropped TIFF, not the much larger NASA URL. The pack and array hashes in provenance.json identify the exact delivered data. No checksum is claimed for the entire SLDEM source tile because only bounded strips were read.

See the main README for NASA/MIT attribution and the papers. CE6_reference_craters.csv is a derived CC BY 4.0 window from Zhao et al., Zenodo 14920942. The window, transformation, source hash and count bins are in surface_reference.json.
