"""Two-tone desk phone stand with a charging-cable slot.

A leaning wedge carved from one block with three angled cuts: a groove the
phone rests in, a back cut that leaves a supporting fin, and a front cut
that leaves a retaining lip. A channel through the lip and base lets a
charging cable reach the phone's port while docked. The body is split at a
single z height into two filament colors, so the AMS swaps only once.

Groove width fits a phone in a case (~11 mm) with room to spare; every
dimension is a parameter. Built for the Bambu P2S profile:

    python examples/phone_stand.py preview
    python examples/phone_stand.py final
"""

from __future__ import annotations

import numpy as np
import trimesh

from solidsmith import Part, difference, intersection, rounded_prism, workflow

# ------------------------------------------------------------ parameters (mm)
BASE_W = 78.0         # footprint, side to side
BASE_D = 84.0         # footprint, front to back
BASE_H = 10.0         # solid slab under everything
TOTAL_H = 68.0        # block height before the cuts shape it

LEAN = 22.0           # degrees the phone reclines from vertical
SLOT_T = 13.0         # groove width: phone + case + wiggle
LIP_T = 10.0          # material in front of the groove, at the groove floor
LIP_RISE = 14.0       # how far the lip stands above the groove floor
BACK_T = 9.0          # supporting fin thickness, perpendicular to the lean

CABLE_W = 14.0        # cable channel through lip, groove floor, and base

LIP_TOP = BASE_H + LIP_RISE
SPLIT_H = LIP_TOP + 2.0  # color boundary: above the lip top, so the swap
                         # plane crosses only the fin (a boundary flush with
                         # the lip top leaves a sub-nozzle veneer on it)
SPLIT_LAP = 0.4       # color bodies overlap this much so the print fuses

MAIN_COLOR = (70, 90, 110)      # slate
ACCENT_COLOR = (230, 214, 184)  # sand


def _leaning(box_dims, local_y, local_z) -> trimesh.Trimesh:
    """A box tipped back by LEAN degrees about the groove's floor line.

    ``local_y``/``local_z`` place the box in the *unrotated* frame, where
    +y is toward the back fin and z=0 is the groove floor; the rotation
    then tips the whole frame back together, so cutters built here stay
    parallel to the phone.
    """
    cutter = trimesh.creation.box(box_dims)
    cutter.apply_translation((0, local_y, local_z))
    lean = trimesh.transformations.rotation_matrix(
        np.radians(-LEAN), (1, 0, 0), (0, 0, 0)
    )
    cutter.apply_transform(lean)
    groove_y = -BASE_D / 2 + LIP_T + SLOT_T / 2
    cutter.apply_translation((0, groove_y, BASE_H))
    return cutter


def build(fast: bool) -> "list[Part]":
    sections = 24 if fast else 96
    block = rounded_prism((BASE_W, BASE_D, TOTAL_H), 8.0, sections=sections)

    groove = _leaning((BASE_W + 20, SLOT_T, 200), local_y=0, local_z=100)
    behind_fin = _leaning((BASE_W + 40, 200, 320), local_y=SLOT_T / 2 + BACK_T + 100, local_z=120)
    before_lip = _leaning((BASE_W + 40, 200, 320), local_y=-(SLOT_T / 2 + 100), local_z=120)

    # the back cut spares the base slab; the front cut spares base + lip
    above = lambda z: trimesh.creation.box(
        (BASE_W + 60, BASE_D + 60, 400), trimesh.transformations.translation_matrix((0, 0, z + 200))
    )
    stand = difference(
        block,
        groove,
        intersection(behind_fin, above(BASE_H)),
        intersection(before_lip, above(LIP_TOP)),
    )

    # the channel leans with the phone: a vertical cutter would exit the
    # fin's slanted face at a glancing angle and leave a feather edge
    notch = 2.0  # cable track carved this deep into the fin's front face
    span = SLOT_T + LIP_T + 12 + notch
    cable = _leaning(
        (CABLE_W, span, 320), local_y=SLOT_T / 2 + notch - span / 2, local_z=0
    )
    stand = difference(stand, cable)

    below_split = trimesh.creation.box((300, 300, SPLIT_H + SPLIT_LAP))
    below_split.apply_translation((0, 0, (SPLIT_H + SPLIT_LAP) / 2))
    above_split = trimesh.creation.box((300, 300, 300))
    above_split.apply_translation((0, 0, 150 + SPLIT_H - SPLIT_LAP))

    return [
        Part(intersection(stand, below_split), ACCENT_COLOR, "base"),
        Part(intersection(stand, above_split), MAIN_COLOR, "fin"),
    ]


if __name__ == "__main__":
    workflow.main(
        build,
        name="phone_stand",
        views={"iso": (28, -50), "front": (12, -90), "side": (8, 0)},
        printer="bambu_p2s",
    )
