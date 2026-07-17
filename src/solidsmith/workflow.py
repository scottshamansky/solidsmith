"""The preview/final iteration loop, packaged.

Scripted models converge on the same habit: every run is either a *preview*
(coarse, fast, renders a PNG to look at) or a *final* (fine, slow, writes
the files you slice), and every preview is archived — script included — so
the look of each iteration and the code that produced it stay side by side.
`main` turns a build function into that CLI:

    from solidsmith import workflow

    def build(fast: bool):
        ...
        return parts            # a mesh, a Part, or a list of them

    if __name__ == "__main__":
        workflow.main(build, name="widget")

    $ python widget.py preview    # out/widget_preview.* + previews/ archive
    $ python widget.py final      # out/widget_final.stl / .3mf
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from solidsmith.export import write_3mf, write_stl
from solidsmith.part import as_parts
from solidsmith.preview import render_views
from solidsmith.report import check


def next_version(previews: Path, name: str) -> int:
    """First unused vN in the archive directory for this model name."""
    pattern = re.compile(rf"^{re.escape(name)}_v(\d+)$")
    taken = [
        int(match.group(1))
        for entry in previews.glob(f"{name}_v*")
        if (match := pattern.match(entry.stem))
    ]
    return max(taken, default=0) + 1


def archive(files, script, previews: Path, name: str) -> int:
    """Copy this iteration's outputs plus its script into previews/ as vN."""
    previews.mkdir(parents=True, exist_ok=True)
    version = next_version(previews, name)
    for source in [*files, script]:
        source = Path(source)
        if source.exists():
            shutil.copy2(source, previews / f"{name}_v{version}{source.suffix}")
    return version


def main(build, name: str, out="out", previews="previews", views=None) -> None:
    """Run a build function as a preview/final CLI (see module docstring).

    ``build(fast: bool)`` should return a mesh, a Part, or a list of Parts —
    coarse when fast is True, print-quality when False.
    """
    parser = argparse.ArgumentParser(description=f"Build {name}")
    parser.add_argument(
        "mode", choices=("preview", "final"), nargs="?", default="preview",
        help="preview: coarse + PNG + archive (default); final: print files",
    )
    args = parser.parse_args()

    parts = as_parts(build(args.mode == "preview"))
    print(check(parts), "\n")

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{name}_{args.mode}"
    written = [
        write_stl(parts, out_dir / f"{stem}.stl"),
        write_3mf(parts, out_dir / f"{stem}.3mf"),
        render_views(parts, out_dir / f"{stem}.png", views=views),
    ]
    for path in written:
        print("wrote", path)

    if args.mode == "preview":
        version = archive(written, Path(sys.argv[0]), Path(previews), name)
        print(f"archived iteration v{version} -> {previews}/")
