"""solidsmith — forge watertight, print-ready 3D parts from Python.

The missing glue between trimesh and your printer: booleans that don't fall
over, 3MF export that keeps its colors, a printability report, and quick
multi-view renders to iterate against.
"""

from solidsmith.export import write_3mf, write_stl
from solidsmith.ops import (
    clean,
    concat,
    difference,
    hex_prism,
    intersection,
    rounded_prism,
    union,
)
from solidsmith.part import Part
from solidsmith.preview import DEFAULT_VIEWS, render_views
from solidsmith.report import DEFAULT_BED, PrintReport, check

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_BED",
    "DEFAULT_VIEWS",
    "Part",
    "PrintReport",
    "check",
    "clean",
    "concat",
    "difference",
    "hex_prism",
    "intersection",
    "render_views",
    "rounded_prism",
    "union",
    "write_3mf",
    "write_stl",
    "__version__",
]
