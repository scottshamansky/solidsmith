"""Pebble planter sculpted from blended SDFs, split into two filament colors.

Three overlapping blobs smooth-union into a pebble, a sphere scoops the
opening, an eroded copy of the body hollows the inside, and a cylinder
punches the drainage hole. The finished solid is then split at a height
into two watertight bodies — pot and rim — so the exported 3MF opens in
the slicer with both filaments already assigned.

Usage:
    python examples/pebble_planter.py           # full quality -> out/
    python examples/pebble_planter.py --fast    # coarse grid for iteration
"""

from __future__ import annotations

import argparse
from pathlib import Path

from solidsmith import Part, check, render_views, sdf, write_3mf, write_stl

# ------------------------------------------------------------ parameters (mm)
WALL = 2.8            # 6+ perimeters at 0.45 mm line width
FLOOR = 3.0
DRAIN_R = 4.0
BLEND = 14.0          # fillet radius where the pebble blobs merge
SCOOP_BLEND = 6.0     # softness of the opening's lip
RIM_Z = 42.0          # where the rim color begins
SPLIT_LAP = 0.8       # color bodies overlap this much (keep > mesh pitch, or they may not touch)

BODY_COLOR = (142, 166, 121)   # sage
RIM_COLOR = (232, 220, 196)    # cream

BOUNDS = ((-52.0, -46.0, -2.0), (52.0, 46.0, 62.0))


def solid():
    body = sdf.smooth_union(
        BLEND,
        sdf.ellipsoid((0, 0, 26), (46, 40, 28)),
        sdf.ellipsoid((13, -7, 32), (36, 32, 26)),
        sdf.sphere((-15, 9, 34), 24),
    )
    body = sdf.intersect(body, sdf.plane())              # flat printable base
    scooped = sdf.smooth_subtract(SCOOP_BLEND, body, sdf.sphere((0, 0, 88), 42))
    cavity = sdf.intersect(
        sdf.offset(body, -WALL),
        sdf.plane(point=(0, 0, FLOOR)),
    )
    return sdf.subtract(scooped, cavity, sdf.vertical_cylinder((0, 0), DRAIN_R))


def build(pitch: float) -> "list[Part]":
    shape = solid()
    pot = sdf.intersect(shape, sdf.plane((0, 0, -1), (0, 0, RIM_Z + SPLIT_LAP)))
    rim = sdf.intersect(shape, sdf.plane((0, 0, 1), (0, 0, RIM_Z - SPLIT_LAP)))
    return [
        Part(sdf.mesh(pot, BOUNDS, pitch), BODY_COLOR, "pot"),
        Part(sdf.mesh(rim, BOUNDS, pitch), RIM_COLOR, "rim"),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="SDF pebble planter, two colors")
    parser.add_argument("--fast", action="store_true", help="coarse grid for iteration")
    parser.add_argument("--out", default="out", help="output directory")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    parts = build(pitch=1.1 if args.fast else 0.55)
    print(check(parts), "\n")
    views = {"iso": (26, -58), "front": (2, -90), "top": (64, -90)}
    print("wrote", write_stl(parts, out / "pebble_planter.stl"))
    print("wrote", write_3mf(parts, out / "pebble_planter.3mf"))
    print("wrote", render_views(parts, out / "pebble_planter.png", views=views))


if __name__ == "__main__":
    main()
