# Contributing

Open an issue with your Blender version, operating system, render engine, selected location and the error traceback or a small reproducer. Include the reported DEM source/grid spacing for terrain issues. Do not attach private files or credentials.

For development, clone this repository, restore the pinned data using `python3 tools/fetch_release_data.py`, and use Blender 5.2 or newer. The release installer contains the same generator code and already includes its offline data.

Keep physical priors separate from artistic appearance controls. Label synthetic sub-DEM detail and preserve source attribution. Include a focused test or render comparison when changing geodesy, population sampling, photometric conventions or Blender registration behavior.

Large `.blend`, `.npz`, and ZIP files belong in release assets, not Git history. The root `release-manifest.json` pins the current release assets and data checksums. Existing results under `tests/` record the runtime and scope of their original execution; only claim a new validation after actually running it.

Code contributions use GPL-3.0-or-later. Do not change third-party dataset licenses or imply mission-agency endorsement.
