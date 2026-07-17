"""Vented storage bin with honeycomb walls and a label tab.

Every dimension is a parameter: stretch the bin, thicken the walls, resize
the hex pattern, or switch the vents and tab off entirely, and it rebuilds
in seconds. The honeycomb is punched straight through both long walls with
one boolean, and the label tab is a continuation of the wall itself so it
prints without supports.

Usage:
    python examples/honeycomb_bin.py           # full quality -> out/
    python examples/honeycomb_bin.py --fast    # coarse corners for iteration
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import trimesh

from solidsmith import (
    Part,
    check,
    difference,
    hex_prism,
    render_views,
    rounded_prism,
    union,
    write_3mf,
    write_stl,
)

# ------------------------------------------------------------ parameters (mm)
LENGTH = 120.0
WIDTH = 80.0
HEIGHT = 55.0
WALL = 1.8            # 4 perimeters at 0.45 mm line width
FLOOR = 2.4
CORNER_R = 9.0

VENTS = True
HEX_R = 5.5           # hexagon circumradius
HEX_WEB = 2.6         # material left between holes
VENT_MARGIN = 8.0     # solid border around the vent field

TAB = True            # label tab rising from the rim of one short wall
TAB_W = 42.0
TAB_H = 16.0          # total tab height; TAB_LAP of it overlaps below the rim
TAB_LAP = 2.0

COLOR = (224, 122, 44)


def build(sections: int = 96) -> trimesh.Trimesh:
    shell = rounded_prism((LENGTH, WIDTH, HEIGHT), CORNER_R, sections=sections)
    cavity = rounded_prism(
        (LENGTH - 2 * WALL, WIDTH - 2 * WALL, HEIGHT),
        max(CORNER_R - WALL, 1.0),
        sections=sections,
    )
    cavity.apply_translation((0, 0, FLOOR))

    cutters = [cavity]
    if VENTS:
        cutters.extend(vent_field())
    bin_ = difference(shell, *cutters)

    if TAB:
        bin_ = union(bin_, label_tab(sections))
    return bin_


def vent_field() -> "list[trimesh.Trimesh]":
    """Honeycomb of hex prisms punched through both long walls at once."""
    x_half = LENGTH / 2 - CORNER_R - VENT_MARGIN - HEX_R
    z_lo = FLOOR + VENT_MARGIN + HEX_R
    z_hi = HEIGHT - VENT_MARGIN - HEX_R
    if x_half <= 0 or z_hi < z_lo:
        return []

    pitch_x = math.sqrt(3) * HEX_R + HEX_WEB
    pitch_z = 1.5 * HEX_R + HEX_WEB * math.cos(math.pi / 6)

    cols = int((2 * x_half) // pitch_x) + 1
    rows = int((z_hi - z_lo) // pitch_z) + 1
    x_start = -(cols - 1) * pitch_x / 2
    z_start = z_lo + (z_hi - z_lo - (rows - 1) * pitch_z) / 2

    lie_flat = trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0))
    hexes = []
    for row in range(rows):
        z = z_start + row * pitch_z
        stagger = pitch_x / 2 if row % 2 else 0.0
        for col in range(-1, cols + 1):
            x = x_start + col * pitch_x + stagger
            if abs(x) > x_half + 1e-6:
                continue
            cutter = hex_prism(HEX_R, WIDTH + 2 * WALL)
            cutter.apply_transform(lie_flat)
            cutter.apply_translation((x, 0, z))
            hexes.append(cutter)
    return hexes


def label_tab(sections: int = 96) -> trimesh.Trimesh:
    """A wall-thick plate continuing one short wall up past the rim.

    Because it sits in the wall's own plane, it prints as more wall — no
    overhang, no supports. The short wall is flat for WIDTH - 2*CORNER_R mm,
    which the tab must fit inside; the top corners are rounded with a pair
    of corner cylinders, same trick as rounded_prism but lying on its side.
    """
    width = min(TAB_W, WIDTH - 2 * CORNER_R - 2)
    corner = 4.0
    x_mid = LENGTH / 2 - WALL / 2
    z_mid = HEIGHT - TAB_LAP + TAB_H / 2

    tall = trimesh.creation.box((WALL, width - 2 * corner, TAB_H))
    tall.apply_translation((x_mid, 0, z_mid))
    wide = trimesh.creation.box((WALL, width, TAB_H - corner))
    wide.apply_translation((x_mid, 0, z_mid - corner / 2))

    lie_on_x = trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0))
    corners = []
    for sy in (-1.0, 1.0):
        cyl = trimesh.creation.cylinder(radius=corner, height=WALL, sections=sections)
        cyl.apply_transform(lie_on_x)
        cyl.apply_translation((x_mid, sy * (width / 2 - corner), z_mid + TAB_H / 2 - corner))
        corners.append(cyl)
    return union(tall, wide, *corners)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parametric honeycomb storage bin")
    parser.add_argument("--fast", action="store_true", help="coarse corners for iteration")
    parser.add_argument("--out", default="out", help="output directory")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    part = Part(build(sections=24 if args.fast else 96), color=COLOR, name="bin")
    print(check(part), "\n")
    hero_views = {"iso": (30, -55), "front": (0, -90), "top": (72, -90)}
    print("wrote", write_stl(part, out / "honeycomb_bin.stl"))
    print("wrote", write_3mf(part, out / "honeycomb_bin.3mf"))
    print("wrote", render_views(part, out / "honeycomb_bin.png", views=hero_views))


if __name__ == "__main__":
    main()
