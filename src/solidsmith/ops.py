"""Boolean modeling that stays watertight.

trimesh's default boolean backend rejects meshes that are fine in practice;
the manifold engine is far more robust but still rewards mesh hygiene on the
way in and out. These wrappers bake both in, so `difference(a, b)` is a thing
you can stop thinking about.
"""

from __future__ import annotations

import numpy as np
import trimesh


def clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Scrub a mesh in place: weld vertices, drop degenerate faces, fix winding.

    Marching-cubes and heavily boolean'd meshes accumulate slivers that make
    later booleans fail; running this between operations keeps them reliable.
    """
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()
    return mesh


def _boolean(kind: str, meshes: "list[trimesh.Trimesh]") -> trimesh.Trimesh:
    prepared = [clean(m.copy()) for m in meshes]
    result = getattr(trimesh.boolean, kind)(prepared, engine="manifold")
    return clean(result)


def union(*meshes: trimesh.Trimesh) -> trimesh.Trimesh:
    """Fuse meshes into one solid."""
    if len(meshes) == 1:
        return clean(meshes[0].copy())
    return _boolean("union", list(meshes))


def difference(base: trimesh.Trimesh, *cutters: trimesh.Trimesh) -> trimesh.Trimesh:
    """Subtract every cutter from base."""
    if not cutters:
        return clean(base.copy())
    return _boolean("difference", [base, *cutters])


def intersection(*meshes: trimesh.Trimesh) -> trimesh.Trimesh:
    """Keep only the volume common to all meshes."""
    return _boolean("intersection", list(meshes))


def concat(*meshes: trimesh.Trimesh) -> trimesh.Trimesh:
    """Append meshes without any boolean (touching bodies that print as one)."""
    return trimesh.util.concatenate(list(meshes))


def rounded_prism(
    extents,
    radius: float,
    sections: int = 64,
) -> trimesh.Trimesh:
    """Rectangular prism with rounded vertical corners, sitting on z=0.

    extents is (x, y, z) in mm; radius rounds the four vertical edges. Built
    from boxes plus corner cylinders so it needs no 2D triangulation deps,
    and clamps the radius rather than erroring when it exceeds the footprint.
    """
    x, y, z = (float(v) for v in extents)
    if min(x, y, z) <= 0:
        raise ValueError(f"extents must be positive, got {extents}")
    radius = max(0.0, min(float(radius), x / 2 - 1e-3, y / 2 - 1e-3))

    if radius < 1e-6:
        prism = trimesh.creation.box((x, y, z))
    else:
        core_x = trimesh.creation.box((x, y - 2 * radius, z))
        core_y = trimesh.creation.box((x - 2 * radius, y, z))
        corners = []
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                cyl = trimesh.creation.cylinder(radius=radius, height=z, sections=sections)
                cyl.apply_translation((sx * (x / 2 - radius), sy * (y / 2 - radius), 0))
                corners.append(cyl)
        prism = union(core_x, core_y, *corners)

    prism.apply_translation((0, 0, z / 2))
    return prism


def hex_prism(circumradius: float, height: float, point_up: bool = True) -> trimesh.Trimesh:
    """Hexagonal prism along z, centered at the origin (honeycomb building block)."""
    hexagon = trimesh.creation.cylinder(radius=circumradius, height=height, sections=6)
    if point_up:
        hexagon.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 6, (0, 0, 1)))
    return hexagon
