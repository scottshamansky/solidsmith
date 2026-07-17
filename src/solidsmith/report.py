"""Answer "will this print?" before wasting filament on finding out."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from solidsmith.part import as_parts

#: Bambu P1/P2/X1-class build volume, mm. Pass your own bed to `check`.
DEFAULT_BED = (256.0, 256.0, 256.0)

_PLATE_TOLERANCE = 0.5  # mm; how far off z=0 still counts as "on the plate"


@dataclass
class PrintReport:
    """What the mesh looks like from a printer's point of view."""

    watertight: bool
    bodies: int
    extents: Tuple[float, float, float]
    volume_cm3: float
    triangles: int
    fits_bed: bool
    bed: Tuple[float, float, float]
    on_plate: bool
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        def mark(ok: bool) -> str:
            return "✔" if ok else "✖"

        x, y, z = self.extents
        bx, by, bz = self.bed
        body_note = "1 body" if self.bodies == 1 else f"{self.bodies} bodies"
        lines = [
            f"{mark(self.watertight)} watertight ({body_note})",
            f"{mark(self.fits_bed)} {x:.1f} × {y:.1f} × {z:.1f} mm "
            f"on a {bx:.0f} × {by:.0f} × {bz:.0f} bed",
            f"{mark(self.on_plate)} first layer on the plate (z=0)",
            f"  {self.volume_cm3:.1f} cm³ · {self.triangles:,} triangles",
        ]
        lines.extend(f"⚠ {w}" for w in self.warnings)
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def check(parts, bed=DEFAULT_BED) -> PrintReport:
    """Inspect a mesh (or Parts) and report printability basics.

    Watertightness is judged per body — touching multi-color bodies are each
    expected to be a closed solid on their own, even though their union is
    what gets printed.
    """
    parts = as_parts(parts)
    meshes = [p.mesh for p in parts]

    watertight = all(m.is_watertight for m in meshes)
    volume = sum(float(m.volume) for m in meshes if m.is_watertight)
    triangles = int(sum(len(m.faces) for m in meshes))

    lows = np.min([m.bounds[0] for m in meshes], axis=0)
    highs = np.max([m.bounds[1] for m in meshes], axis=0)
    extents = tuple(float(v) for v in (highs - lows))
    fits = all(e <= b + 1e-6 for e, b in zip(extents, bed))

    z_low = float(lows[2])
    on_plate = abs(z_low) <= _PLATE_TOLERANCE

    warnings = []
    if not watertight:
        leaky = [p.name for p in parts if not p.mesh.is_watertight]
        warnings.append(
            "not watertight: " + ", ".join(leaky) + " — run ops.clean() or check booleans"
        )
    if not fits:
        warnings.append("model exceeds the bed; scale it down or split the print")
    if z_low > _PLATE_TOLERANCE:
        warnings.append(f"model floats {z_low:.1f} mm above the plate")
    if z_low < -_PLATE_TOLERANCE:
        warnings.append(f"model extends {-z_low:.1f} mm below the plate")

    return PrintReport(
        watertight=watertight,
        bodies=len(parts),
        extents=extents,
        volume_cm3=volume / 1000.0,
        triangles=triangles,
        fits_bed=fits,
        bed=tuple(float(b) for b in bed),
        on_plate=on_plate,
        warnings=warnings,
    )
