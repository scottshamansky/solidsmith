"""Sculpt organic shapes as blended signed distance fields.

Booleans give you crisp mechanical edges; SDFs give you clay. Describe a
shape as distance functions over space, blend them with smooth minimums so
joints read as fillets instead of seams, then pull a watertight mesh out
with marching cubes and Taubin smoothing.

A field is any callable mapping an (N, 3) array of points to (N,) signed
distances, negative inside. Compose them functionally:

    body = sdf.smooth_union(12, sdf.sphere((0, 0, 30), 25),
                                sdf.ellipsoid((0, 18, 22), (20, 26, 16)))
    solid = sdf.intersect(body, sdf.plane())        # flat print base at z=0
    mesh = sdf.mesh(solid, bounds=((-30, -30, 0), (30, 50, 50)), pitch=0.5)
"""

from __future__ import annotations

import numpy as np
import trimesh

from solidsmith.ops import clean

# ------------------------------------------------------------------ primitives


def sphere(center, radius: float):
    center = np.asarray(center, dtype=np.float64)

    def field(p):
        return np.linalg.norm(p - center, axis=-1) - radius

    return field


def ellipsoid(center, radii):
    """Inigo Quilez's ellipsoid distance bound — exact enough for blending."""
    center = np.asarray(center, dtype=np.float64)
    radii = np.asarray(radii, dtype=np.float64)

    def field(p):
        q = (p - center) / radii
        k0 = np.linalg.norm(q, axis=-1)
        k1 = np.linalg.norm(q / radii, axis=-1)
        return np.where(k1 > 0, k0 * (k0 - 1.0) / np.maximum(k1, 1e-12), -radii.min())

    return field


def capsule(a, b, radius_a: float, radius_b: "float | None" = None):
    """Line-segment capsule from a to b; give two radii for a taper."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    r2 = radius_a if radius_b is None else radius_b

    def field(p):
        pa = p - a
        ba = b - a
        h = np.clip((pa @ ba) / (ba @ ba), 0.0, 1.0)
        radius = radius_a + (r2 - radius_a) * h
        return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - radius

    return field


def rounded_box(center, extents, radius: float):
    center = np.asarray(center, dtype=np.float64)
    half = np.asarray(extents, dtype=np.float64) / 2.0 - radius

    def field(p):
        q = np.abs(p - center) - half
        outside = np.linalg.norm(np.maximum(q, 0.0), axis=-1)
        inside = np.minimum(q.max(axis=-1), 0.0)
        return outside + inside - radius

    return field


def plane(normal=(0, 0, 1), point=(0, 0, 0)):
    """Half-space keeping everything on the side the normal points toward."""
    normal = np.asarray(normal, dtype=np.float64)
    normal = normal / np.linalg.norm(normal)
    point = np.asarray(point, dtype=np.float64)

    def field(p):
        return -((p - point) @ normal)

    return field


def vertical_cylinder(center_xy, radius: float):
    """Infinite cylinder along z — cap it by intersecting with planes."""
    center = np.asarray(center_xy, dtype=np.float64)

    def field(p):
        return np.linalg.norm(p[..., :2] - center, axis=-1) - radius

    return field


# ----------------------------------------------------------------- combinators


def _smin(a, b, k: float):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def union(*fields):
    return lambda p: np.minimum.reduce([f(p) for f in fields])


def intersect(*fields):
    return lambda p: np.maximum.reduce([f(p) for f in fields])


def subtract(base, *cutters):
    cut = union(*cutters)
    return lambda p: np.maximum(base(p), -cut(p))


def smooth_union(k: float, *fields):
    """Union with radius-k fillets where surfaces meet (the clay look)."""

    def field(p):
        values = [f(p) for f in fields]
        out = values[0]
        for v in values[1:]:
            out = _smin(out, v, k)
        return out

    return field


def smooth_subtract(k: float, base, *cutters):
    """Subtract with a radius-k fillet along the cut."""
    cut = union(*cutters)
    return lambda p: -_smin(-base(p), cut(p), k)


def offset(base, distance: float):
    """Positive distance inflates the solid; negative erodes it."""
    return lambda p: base(p) - distance


def shell(base, thickness: float):
    """Hollow a solid into a wall of the given thickness."""
    return lambda p: np.abs(base(p)) - thickness / 2.0


# ---------------------------------------------------------------- meshing


def mesh(
    field,
    bounds,
    pitch: float = 0.8,
    smooth_iterations: int = 10,
) -> trimesh.Trimesh:
    """Sample the field on a grid and extract a watertight surface.

    bounds is ((x0, y0, z0), (x1, y1, z1)) in mm and should enclose the
    solid with a little margin; pitch is the grid spacing (smaller = finer,
    cost grows with the cube). Taubin smoothing removes the marching-cubes
    staircase without shrinking the shape.
    """
    from skimage import measure

    lo = np.asarray(bounds[0], dtype=np.float64)
    hi = np.asarray(bounds[1], dtype=np.float64)
    if np.any(hi <= lo):
        raise ValueError(f"bad bounds {bounds}")

    steps = np.maximum(np.ceil((hi - lo) / pitch).astype(int) + 1, 2)
    axes = [np.linspace(lo[i], hi[i], steps[i]) for i in range(3)]
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    volume = field(grid.reshape(-1, 3)).reshape(grid.shape[:3])

    if volume.min() > 0 or volume.max() < 0:
        raise ValueError(
            "field never crosses zero inside bounds — nothing to mesh "
            f"(min {volume.min():.2f}, max {volume.max():.2f})"
        )

    spacing = tuple((hi[i] - lo[i]) / (steps[i] - 1) for i in range(3))
    vertices, faces, _, _ = measure.marching_cubes(volume, level=0.0, spacing=spacing)
    result = trimesh.Trimesh(vertices=vertices + lo, faces=faces)

    clean(result)
    if smooth_iterations > 0:
        trimesh.smoothing.filter_taubin(result, lamb=0.5, nu=-0.53, iterations=smooth_iterations)
        clean(result)
    return result
