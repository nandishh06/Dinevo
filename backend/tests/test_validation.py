"""Validation unit tests."""

from __future__ import annotations

from pathlib import Path

from app.validation.glb import (
    validate_generated_assets,
    _glb_container_errors,
)
from tests.conftest import make_glb_bytes, make_real_glb_bytes


def test_is_glb_valid_container(tmp_path: Path) -> None:
    p = tmp_path / "x.glb"
    p.write_bytes(make_glb_bytes())
    assert _glb_container_errors(p) == []


def test_is_glb_rejects_non_gltf(tmp_path: Path) -> None:
    p = tmp_path / "x.glb"
    p.write_bytes(b"not a glb file at all......")
    errors = _glb_container_errors(p)
    assert any("magic" in e for e in errors)


def test_glb_rejects_truncated(tmp_path: Path) -> None:
    p = tmp_path / "x.glb"
    p.write_bytes(b"glTF")  # too short
    errors = _glb_container_errors(p)
    assert any("truncated" in e or "header" in e for e in errors)


def test_glb_rejects_bad_json_chunk(tmp_path: Path) -> None:
    import struct

    # Header declares a JSON chunk whose content is not valid JSON.
    json_chunk = b"<<<not json>>>"
    padded = json_chunk + b" " * ((4 - len(json_chunk) % 4) % 4)
    total = 12 + 8 + len(padded)
    p = tmp_path / "x.glb"
    p.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(padded), b"JSON")
        + padded
    )
    errors = _glb_container_errors(p)
    assert any("JSON" in e for e in errors)


def test_validation_passes_with_glb_and_usdz(tmp_path: Path) -> None:
    glb = tmp_path / "d.glb"
    glb.write_bytes(make_real_glb_bytes())
    usdz = tmp_path / "d.usdz"
    usdz.write_bytes(b"usdz")
    result = validate_generated_assets(glb, usdz)
    assert result.ok is True
    assert result.errors == []


def test_validation_fails_missing_glb(tmp_path: Path) -> None:
    result = validate_generated_assets(tmp_path / "missing.glb", None)
    assert result.ok is False
    assert "GLB file missing" in result.errors


def test_validation_fails_empty_usdz(tmp_path: Path) -> None:
    glb = tmp_path / "d.glb"
    glb.write_bytes(make_real_glb_bytes())
    usdz = tmp_path / "d.usdz"
    usdz.write_bytes(b"")  # empty
    result = validate_generated_assets(glb, usdz)
    assert result.ok is False
    assert "USDZ missing or empty" in result.errors


def test_validation_fails_bad_glb_content(tmp_path: Path) -> None:
    glb = tmp_path / "d.glb"
    glb.write_bytes(b"garbage-not-a-glb")
    usdz = tmp_path / "d.usdz"
    usdz.write_bytes(b"usdz")
    result = validate_generated_assets(glb, usdz)
    assert result.ok is False
    assert any("magic" in e for e in result.errors)


def test_validation_size_band(tmp_path: Path) -> None:
    glb = tmp_path / "d.glb"
    glb.write_bytes(make_real_glb_bytes())
    result = validate_generated_assets(glb, None, max_glb_bytes=4)
    assert result.ok is False
    assert any("outside sane range" in e for e in result.errors)
