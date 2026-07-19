"""Named printers, so checks judge against a real machine instead of a magic bed."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Printer:
    """One machine's limits as seen by the printability checks.

    ``bed`` is the usable build volume in mm. ``nozzle`` is the installed
    nozzle diameter in mm; walls thinner than one extrusion of it cannot
    be printed and future checks use it as the floor for feature size.
    """

    name: str
    bed: Tuple[float, float, float]
    nozzle: float = 0.4


BAMBU_X1C = Printer("Bambu X1C / P1S", (256.0, 256.0, 256.0))
BAMBU_P2S = Printer("Bambu P2S", (256.0, 256.0, 256.0))
BAMBU_A1 = Printer("Bambu A1", (256.0, 256.0, 256.0))
BAMBU_A1_MINI = Printer("Bambu A1 mini", (180.0, 180.0, 180.0))
PRUSA_MK4 = Printer("Prusa MK4", (250.0, 210.0, 220.0))
ENDER_3 = Printer("Creality Ender 3", (220.0, 220.0, 250.0))

#: What `check` assumes when no printer is named.
DEFAULT_PRINTER = BAMBU_X1C

PRINTERS = {
    "bambu_x1c": BAMBU_X1C,
    "bambu_p1s": BAMBU_X1C,
    "bambu_p2s": BAMBU_P2S,
    "bambu_a1": BAMBU_A1,
    "bambu_a1_mini": BAMBU_A1_MINI,
    "prusa_mk4": PRUSA_MK4,
    "ender_3": ENDER_3,
}


def printer(name: str) -> Printer:
    """Look up a built-in profile by slug, e.g. ``printer("bambu_a1_mini")``."""
    try:
        return PRINTERS[name]
    except KeyError:
        known = ", ".join(sorted(PRINTERS))
        raise KeyError(f"unknown printer {name!r}; built-ins: {known}") from None
