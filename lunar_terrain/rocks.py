"""Deterministic fractured rock prototypes, with geometry reserved for near rocks.

Dimensions are normalized to one metre equivalent projected diameter. Detail is
an artist-authored interpretation of mission photographs, not a rock scan.
"""
import math
import bmesh
import numpy as np

SCHEMA = 2


def hull_area(points):
    points = sorted(set(map(tuple, points.tolist())))
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower, upper = [], []
    for pt in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], pt) <= 0:
            lower.pop()
        lower.append(pt)
    for pt in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], pt) <= 0:
            upper.pop()
        upper.append(pt)
    h = np.asarray(lower[:-1]+upper[:-1])
    return abs(np.dot(h[:, 0], np.roll(h[:, 1], 1))-
               np.dot(h[:, 1], np.roll(h[:, 0], 1)))/2


def populate_mesh(mesh, seed, index):
    """Replace an owned prototype in place; keep linked instances and material."""
    detailed = index < 12
    rng = np.random.default_rng(seed+900+index)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=5 if detailed else 2, radius=1.)
    bm.to_mesh(mesh)
    bm.free()
    v = np.empty((len(mesh.vertices), 3), np.float32)
    mesh.vertices.foreach_get('co', v.ravel())
    unit = v.copy()
    normals = rng.normal(size=(14, 3))
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    offsets = rng.uniform(.45, .88, 14)
    dots = v @ normals.T
    factors = np.min(np.where(dots > 1e-5, offsets/np.maximum(dots, 1e-5), 100), axis=1)
    v *= np.minimum(factors, 1.05)[:, None]
    v[:, 2] *= rng.uniform(.48, .82)
    v[:, 2] = np.maximum(v[:, 2], -.16)
    if detailed:
        # Coherent surface chips, not independent jitter at every mesh vertex.
        waves = rng.normal(size=(9, 3))
        waves /= np.linalg.norm(waves, axis=1)[:, None]
        phases = rng.uniform(0, 2*math.pi, 9)
        noise = np.sin(v @ (waves*28).T+phases).mean(axis=1)
        v += unit*(.022*noise)[:, None]
        # Broken stress fractures cut the silhouette and receive true shadows.
        for j in range(3):
            n = normals[j]
            line = v@n-rng.uniform(-.32, .32)
            line += .017*np.sin(v@waves[j]*19+phases[j])
            groove = np.exp(-(line/rng.uniform(.018, .032))**2)
            broken = np.clip(.65+.5*np.sin(v@waves[j+3]*11+phases[j+3]), .15, 1)
            v -= unit*(.018*groove*broken)[:, None]
        # A few shallow impact chips; most surfaces remain dust coated.
        for j in range(10):
            c = v[int(rng.integers(len(v)))].copy()
            d2 = np.sum((v-c)**2, axis=1)
            v -= unit*(rng.uniform(.006, .017)*np.exp(-d2/rng.uniform(.002, .007)))[:, None]
        v[:, 2] = np.maximum(v[:, 2], -.16)
    v *= math.sqrt((math.pi/4)/hull_area(v[:, :2]))
    mesh.vertices.foreach_set('co', v.ravel())
    mesh.update()
    mesh.polygons.foreach_set('use_smooth', np.ones(len(mesh.polygons), bool))
    mesh.set_sharp_from_angle(angle=math.radians(30))
    mesh['lunar_rock_schema'] = SCHEMA
    mesh['detail_level'] = 'near: fractured geometry' if detailed else 'far/small: low poly'

