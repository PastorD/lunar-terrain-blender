"""Convert a georeferenced lunar GeoTIFF to an add-on pack. Requires numpy/rasterio."""
from pathlib import Path
import argparse, json, math, os
import numpy as np
import rasterio
from rasterio.windows import Window

R = 1737400.0

def convert(source, destination, window=None, vertical_scale=1.0):
    destination = Path(destination)
    if destination.suffix.lower() != '.npz':
        raise ValueError('Output must have the .npz extension')
    if not math.isfinite(vertical_scale) or vertical_scale <= 0:
        raise ValueError('Vertical scale must be positive and finite')
    with rasterio.open(source) as dataset:
        if dataset.count != 1 or not dataset.crs:
            raise ValueError('Expected one elevation band with an explicit lunar CRS')
        win = Window(*window) if window is not None else Window(0, 0, dataset.width, dataset.height)
        if min(win.col_off, win.row_off) < 0 or min(win.width, win.height) < 4:
            raise ValueError('Window must be inside the source and at least 4 × 4 cells')
        if win.col_off + win.width > dataset.width or win.row_off + win.height > dataset.height:
            raise ValueError('Window exceeds source bounds')
        if win.width * win.height > 80000000:
            raise ValueError('Crop to no more than 80 million cells')
        t = dataset.window_transform(win)
        if abs(t.b) > 1e-10 or abs(t.d) > 1e-10 or t.a <= 0 or t.e >= 0 or abs(t.a + t.e) > t.a * 1e-6:
            raise ValueError('Expected north-up, unrotated square pixels; reproject first')
        crs = dataset.crs.to_dict()
        a, b = float(crs.get('R', crs.get('a', 0))), float(crs.get('R', crs.get('b', crs.get('a', 0))))
        if abs(a - R) > .01 or abs(b - R) > .01:
            raise ValueError('CRS must use a lunar sphere of radius 1737400 metres')
        m = dict(schema=1, radius_m=R, title=Path(source).stem,
                 scale=1., periodic=False, source_file=Path(source).name,
                 source_window=[int(v) for v in (win.col_off, win.row_off, win.width, win.height)],
                 source_crs=dataset.crs.to_wkt(), vertical_units='metres above 1737400 m sphere')
        proj = crs.get('proj')
        if proj in ('longlat', 'latlong', 'lonlat'):
            m.update(projection='cylindrical', west=t.c, north=t.f, ppd=1/t.a, posting_m=t.a*math.pi*R/180)
            m['periodic'] = abs(win.width*t.a - 360) < 1e-6
        elif proj == 'stere':
            lat0 = float(crs.get('lat_0', 0))
            if abs(abs(lat0)-90) > 1e-8 or any(abs(float(crs.get(k, 0))) > 1e-8 for k in ('lon_0','x_0','y_0')):
                raise ValueError('Stereographic must be centred on a pole, longitude 0, with no false offsets')
            if abs(float(crs.get('lat_ts', lat0))-lat0) > 1e-8 or abs(float(crs.get('k', crs.get('k_0', 1)))-1) > 1e-8:
                raise ValueError('Stereographic must have unit scale at the pole')
            if crs.get('units', 'm') != 'm': raise ValueError('Projection units must be metres')
            m.update(projection='south_polar' if lat0 < 0 else 'north_polar', west=t.c, north=t.f, pixel_m=t.a, posting_m=t.a)
        elif proj == 'eqc':
            if any(abs(float(crs.get(k,0)))>1e-8 for k in ('x_0','y_0')):raise ValueError('Equirectangular false offsets must be zero')
            if crs.get('units','m')!='m':raise ValueError('Projection units must be metres')
            m.update(projection='eqc',west=t.c,north=t.f,pixel_m=t.a,posting_m=t.a,standard_parallel=float(crs.get('lat_ts',0)),origin_latitude=float(crs.get('lat_0',0)),central_longitude=float(crs.get('lon_0',0)))
        else:
            raise ValueError('Unsupported projection; use lunar geographic, simple cylindrical or polar stereographic')
        heights = dataset.read(1, window=win, masked=True).astype(np.float32).filled(np.nan) * vertical_scale
        finite = heights[np.isfinite(heights)]
        if not len(finite) or np.max(np.abs(finite)) >= 30000:
            raise ValueError('Expected elevations in metres relative to the lunar sphere; check vertical scale')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.partial')
    try:
        with temporary.open('wb') as f:
            np.savez_compressed(f, elevation=heights, metadata=np.array(json.dumps(m)))
        os.replace(temporary, destination)
    finally:
        if temporary.exists(): temporary.unlink()
    return m

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input'); parser.add_argument('output')
    parser.add_argument('--window', nargs=4, type=int, metavar=('COL','ROW','WIDTH','HEIGHT'))
    parser.add_argument('--vertical-scale', type=float, default=1.)
    args = parser.parse_args()
    print(json.dumps(convert(args.input, args.output, args.window, args.vertical_scale), indent=2))
