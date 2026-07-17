"""Behavior tests: geometry stays watertight, exports keep their promises."""

import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pytest
import trimesh

from solidsmith import (
    Part,
    check,
    difference,
    intersection,
    render_views,
    rounded_prism,
    sdf,
    union,
    write_3mf,
    write_stl,
)

CORE_NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}


def test_rounded_prism_is_watertight_and_sized():
    prism = rounded_prism((40, 30, 20), radius=6, sections=32)
    assert prism.is_watertight
    assert np.allclose(prism.extents, (40, 30, 20), atol=1e-6)
    assert prism.bounds[0][2] == pytest.approx(0, abs=1e-9)


def test_difference_punches_a_through_hole():
    base = rounded_prism((30, 30, 10), radius=4)
    drill = trimesh.creation.cylinder(radius=5, height=40)
    drill.apply_translation((0, 0, 5))
    result = difference(base, drill)
    assert result.is_watertight
    assert result.volume < base.volume
    assert result.euler_number == 0  # genus 1: the hole goes all the way through


def test_union_and_intersection_volumes():
    a = trimesh.creation.box((10, 10, 10))
    b = trimesh.creation.box((10, 10, 10))
    b.apply_translation((5, 0, 0))
    fused = union(a, b)
    common = intersection(a, b)
    assert fused.is_watertight and common.is_watertight
    assert fused.volume == pytest.approx(1500, rel=1e-3)
    assert common.volume == pytest.approx(500, rel=1e-3)


def test_write_stl_round_trips(tmp_path):
    prism = rounded_prism((20, 15, 10), radius=3)
    path = write_stl(prism, tmp_path / "prism.stl")
    loaded = trimesh.load(path)
    assert loaded.is_watertight
    assert loaded.volume == pytest.approx(prism.volume, rel=1e-6)


def test_write_3mf_keeps_colors(tmp_path):
    a = trimesh.creation.box((20, 20, 10))
    a.apply_translation((0, 0, 5))
    b = trimesh.creation.cylinder(radius=6, height=8)
    b.apply_translation((0, 0, 14))
    path = write_3mf(
        [Part(a, (30, 120, 220), "base"), Part(b, (240, 200, 40), "cap")],
        tmp_path / "model.3mf",
    )

    xml = zipfile.ZipFile(path).read("3D/3dmodel.model")
    root = ET.fromstring(xml)
    resources = root.find("m:resources", CORE_NS)
    materials = resources.find("m:basematerials", CORE_NS)
    bases = materials.findall("m:base", CORE_NS)
    assert [b.get("displaycolor") for b in bases] == ["#1E78DC", "#F0C828"]
    assert [b.get("name") for b in bases] == ["base", "cap"]

    objects = [
        o for o in resources.findall("m:object", CORE_NS)
        if o.find("m:mesh", CORE_NS) is not None
    ]
    assert len(objects) == 2
    assert {o.get("pid") for o in objects} == {materials.get("id")}
    assert sorted(o.get("pindex") for o in objects) == ["0", "1"]


def test_check_reports_problems():
    tall = trimesh.creation.box((10, 10, 300))
    tall.apply_translation((0, 0, 150))
    report = check(tall)
    assert not report.fits_bed
    assert any("exceeds the bed" in w for w in report.warnings)

    floater = trimesh.creation.box((10, 10, 10))
    floater.apply_translation((0, 0, 30))
    report = check(floater)
    assert not report.on_plate
    assert any("floats" in w for w in report.warnings)

    leaky = trimesh.Trimesh(
        vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0]], faces=[[0, 1, 2]]
    )
    report = check(leaky)
    assert not report.watertight


def test_check_happy_path_summary():
    box = trimesh.creation.box((10, 10, 10))
    box.apply_translation((0, 0, 5))
    report = check(box)
    assert report.watertight and report.fits_bed and report.on_plate
    assert report.warnings == []
    assert "✔" in report.summary() and "⚠" not in report.summary()


def test_sdf_sphere_meshes_to_expected_volume():
    field = sdf.sphere((0, 0, 0), 10)
    mesh = sdf.mesh(field, ((-12, -12, -12), (12, 12, 12)), pitch=0.8)
    assert mesh.is_watertight
    assert mesh.volume == pytest.approx(4 / 3 * np.pi * 10**3, rel=0.05)
    assert np.allclose(mesh.extents, 20, atol=1.0)


def test_sdf_smooth_union_adds_neck_material():
    left = sdf.sphere((-6, 0, 0), 5)
    right = sdf.sphere((6, 0, 0), 5)
    blended = sdf.mesh(
        sdf.smooth_union(5, left, right), ((-14, -8, -8), (14, 8, 8)), pitch=0.6
    )
    plain = sdf.mesh(
        sdf.union(left, right), ((-14, -8, -8), (14, 8, 8)), pitch=0.6
    )
    assert blended.is_watertight
    assert blended.body_count == 1
    assert blended.volume > plain.volume


def test_sdf_mesh_rejects_empty_field():
    with pytest.raises(ValueError, match="never crosses zero"):
        sdf.mesh(sdf.sphere((0, 0, 0), 1), ((5, 5, 5), (8, 8, 8)), pitch=0.5)


def test_render_views_writes_a_real_png(tmp_path):
    box = trimesh.creation.box((10, 10, 10))
    box.apply_translation((0, 0, 5))
    out = tmp_path / "views.png"
    render_views(box, out)
    assert out.stat().st_size > 10_000
