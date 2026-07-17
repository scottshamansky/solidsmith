"""Multi-view PNG renders with no GUI, GPU, or external renderer.

matplotlib's 3D toolkit is slow for interaction but fine for stills: flat
Lambert shading, three or four named camera angles, one image. The point is
a feedback loop measured in seconds — iterate on the cheap render and only
slice when the shape is right.
"""

from __future__ import annotations

import numpy as np

from solidsmith.part import as_parts

#: name -> (elevation, azimuth) in degrees
DEFAULT_VIEWS = {
    "front": (8, -90),
    "iso": (26, -52),
    "side": (8, 0),
    "top": (74, -90),
}

_LIGHT = np.array([0.35, -0.45, 0.82])
_LIGHT = _LIGHT / np.linalg.norm(_LIGHT)


def render_views(parts, path, views=None, dpi: int = 140, background: str = "white"):
    """Render every part into one PNG with a subplot per camera angle.

    ``parts`` may be a mesh, a Part, or a sequence of either; ``views`` maps
    view names to (elevation, azimuth) tuples and defaults to DEFAULT_VIEWS.
    Returns the path it wrote.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    parts = as_parts(parts)
    views = dict(views) if views else dict(DEFAULT_VIEWS)

    spans_all = np.concatenate([p.mesh.bounds for p in parts], axis=0)
    max_edge = 0.04 * float(np.ptp(spans_all, axis=0).max())

    # one combined triangle soup so depth sorting works across parts;
    # long edges get subdivided first because the painter's algorithm
    # mis-sorts large triangles and streaks flat faces
    triangles, colors = [], []
    for part in parts:
        mesh = part.mesh
        if max_edge > 0 and len(mesh.faces):
            mesh = mesh.subdivide_to_size(max_edge, max_iter=12)
        normals = np.nan_to_num(np.asarray(mesh.face_normals, dtype=np.float64))
        # multiply-and-sum rather than matmul: Accelerate BLAS on macOS emits
        # spurious floating-point warnings for tiny matmuls
        lambert = np.clip(np.sum(normals * _LIGHT, axis=1), 0.0, 1.0)
        # shade in linear light, then back to sRGB, so colors stay saturated
        base = (np.array(part.color, dtype=np.float64) / 255.0) ** 2.2
        lit = base[None, :] * (0.35 + 0.65 * lambert)[:, None]
        triangles.append(mesh.triangles)
        colors.append(np.clip(lit, 0.0, 1.0) ** (1 / 2.2))
    triangles = np.concatenate(triangles)
    colors = np.concatenate(colors)

    bounds_min = triangles.reshape(-1, 3).min(axis=0)
    bounds_max = triangles.reshape(-1, 3).max(axis=0)
    spans = np.maximum(bounds_max - bounds_min, 1e-6)
    pad = 0.04 * spans.max()

    n = len(views)
    fig = plt.figure(figsize=(3.7 * n, 4.1), facecolor=background)
    for i, (name, (elev, azim)) in enumerate(views.items(), start=1):
        ax = fig.add_subplot(1, n, i, projection="3d", facecolor=background)
        # edges painted like their faces hide antialiasing seams between triangles
        collection = Poly3DCollection(
            triangles, facecolors=colors, edgecolors=colors, linewidths=0.3
        )
        ax.add_collection3d(collection)
        ax.set_xlim(bounds_min[0] - pad, bounds_max[0] + pad)
        ax.set_ylim(bounds_min[1] - pad, bounds_max[1] + pad)
        ax.set_zlim(bounds_min[2] - pad, bounds_max[2] + pad)
        ax.set_box_aspect(spans + 2 * pad)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(name, fontsize=10, color="#666666", pad=2)

    fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.02, wspace=0.02)
    fig.savefig(path, dpi=dpi, facecolor=background)
    plt.close(fig)
    return path
