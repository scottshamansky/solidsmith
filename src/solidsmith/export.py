"""Export meshes to print-ready files.

STL is the easy half. 3MF is the interesting one: trimesh writes valid 3MF
geometry but silently drops color, so every body opens gray in the slicer.
`write_3mf` post-processes the archive it writes — injecting a real
``<basematerials>`` resource and tagging each body with a material index —
so a multi-color model opens with its filament assignments already in place.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import trimesh

from solidsmith.ops import concat
from solidsmith.part import Part, as_parts

_CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
_MODEL_ENTRY = "3D/3dmodel.model"


def write_stl(parts, path) -> Path:
    """Write one binary STL. Multiple parts are concatenated (STL has no color)."""
    path = Path(path)
    parts = as_parts(parts)
    mesh = parts[0].mesh if len(parts) == 1 else concat(*(p.mesh for p in parts))
    mesh.export(path)
    return path


def write_3mf(parts, path) -> Path:
    """Write a single 3MF containing every part as a separately colored body."""
    path = Path(path)
    parts = as_parts(parts)

    scene = trimesh.Scene()
    for i, part in enumerate(parts):
        # zero-padded prefix pins a stable object order in the archive
        scene.add_geometry(part.mesh, geom_name=f"{i:03d}_{part.name}")
    scene.export(path)

    _inject_materials(path, parts)
    return path


def _inject_materials(path: Path, parts: "list[Part]") -> None:
    """Rewrite the 3MF's model XML with basematerials + per-object material refs."""
    with zipfile.ZipFile(path, "r") as zf:
        entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}
    if _MODEL_ENTRY not in entries:
        raise ValueError(f"{path} has no {_MODEL_ENTRY}; not a 3MF written by trimesh?")

    ET.register_namespace("", _CORE_NS)
    root = ET.fromstring(entries[_MODEL_ENTRY])
    ns = {"m": _CORE_NS}
    resources = root.find("m:resources", ns)
    if resources is None:
        raise ValueError("3MF model has no <resources> element")

    objects = [
        obj for obj in resources.findall("m:object", ns)
        if obj.find("m:mesh", ns) is not None
    ]
    if len(objects) != len(parts):
        raise ValueError(
            f"expected {len(parts)} mesh objects in the 3MF, found {len(objects)}"
        )

    used_ids = [int(obj.get("id")) for obj in resources.findall("m:object", ns)]
    material_id = str(max(used_ids) + 1)

    materials = ET.Element(f"{{{_CORE_NS}}}basematerials", {"id": material_id})
    for part in parts:
        r, g, b = (int(c) for c in part.color)
        ET.SubElement(
            materials,
            f"{{{_CORE_NS}}}base",
            {"name": part.name, "displaycolor": f"#{r:02X}{g:02X}{b:02X}"},
        )
    resources.insert(0, materials)

    for index, obj in enumerate(objects):
        obj.set("pid", material_id)
        obj.set("pindex", str(index))

    entries[_MODEL_ENTRY] = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
