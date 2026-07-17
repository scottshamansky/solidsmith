"""Desk organizer block for 1/4" hex driver bits.

A rounded block with a staggered grid of hex sockets, sized for standard
6.35 mm across-flats bits with a 0.2 mm slide-fit clearance — loose enough
to pull a bit out one-handed, snug enough that nothing rattles.

This example uses solidsmith.workflow, so it gets the preview/final CLI
and the versioned previews/ archive for free:

    python examples/bit_organizer.py preview
    python examples/bit_organizer.py final
"""

from __future__ import annotations

import math

import trimesh

from solidsmith import difference, hex_prism, rounded_prism, workflow, Part

# ------------------------------------------------------------ parameters (mm)
ROWS = 2
COLS = 8
PITCH = 11.0          # socket center spacing, both directions
BIT_FLATS = 6.35      # 1/4" hex bit, across flats
CLEARANCE = 0.2       # added across flats: slide fit, no rattle
SOCKET_DEPTH = 14.0

MARGIN = 7.0          # block material beyond the outer sockets
BASE_H = 22.0
CORNER_R = 6.0
COLOR = (105, 125, 150)


def build(fast: bool) -> Part:
    sections = 24 if fast else 96
    length = (COLS - 1) * PITCH + 2 * MARGIN
    width = (ROWS - 1) * PITCH + 2 * MARGIN
    block = rounded_prism((length, width, BASE_H), CORNER_R, sections=sections)

    socket_r = (BIT_FLATS + CLEARANCE) / math.sqrt(3)  # across-flats -> circumradius
    sockets = []
    for row in range(ROWS):
        for col in range(COLS):
            x = (col - (COLS - 1) / 2) * PITCH
            y = (row - (ROWS - 1) / 2) * PITCH
            socket = hex_prism(socket_r, SOCKET_DEPTH + 1)
            socket.apply_translation((x, y, BASE_H - SOCKET_DEPTH / 2 + 0.5))
            sockets.append(socket)

    return Part(difference(block, *sockets), COLOR, "organizer")


if __name__ == "__main__":
    workflow.main(build, name="bit_organizer", views={"iso": (32, -55), "top": (75, -90)})
