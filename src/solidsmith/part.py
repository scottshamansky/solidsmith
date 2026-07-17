"""A mesh plus how it should appear when exported or rendered."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import trimesh


@dataclass
class Part:
    """One printable body: a mesh, a display color, and a name.

    Color is sRGB 0-255. A multi-color model is just a list of Parts (one
    per filament); exported together they become a single 3MF that opens in
    the slicer with every body already assigned its color.
    """

    mesh: trimesh.Trimesh
    color: Tuple[int, int, int] = (140, 140, 145)
    name: str = "part"


def as_parts(obj) -> "list[Part]":
    """Normalize a Part, a mesh, or a sequence of either into a list of Parts."""
    if isinstance(obj, Part):
        return [obj]
    if isinstance(obj, trimesh.Trimesh):
        return [Part(obj)]
    parts = []
    for i, item in enumerate(obj):
        if isinstance(item, Part):
            parts.append(item)
        elif isinstance(item, trimesh.Trimesh):
            parts.append(Part(item, name=f"part_{i}"))
        else:
            raise TypeError(f"expected Part or Trimesh, got {type(item).__name__}")
    if not parts:
        raise ValueError("no parts given")
    return parts
