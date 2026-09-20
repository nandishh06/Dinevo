"""Minimal automated validation for generated assets.

Rule: automated validation NEVER publishes. It only reports pass/fail; the
GenerationService sets READY_FOR_REVIEW (or FAILED) based on it. Human visual
approval stays mandatory and happens later at the APPROVED step.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path

# GLB = 12-byte header (magic "glTF" + version + length) + JSON chunk.
_GLB_MAGIC = b"glTF"
_GLB_CHUNK_TYPE_JSON = b"JSON"
_GLB_HEADER_SIZE = 12
_GLB_CHUNK_HEADER_SIZE = 8


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def _ok() -> ValidationResult:
    return ValidationResult(ok=True, errors=[], warnings=[])


def _fail(errors: list[str]) -> ValidationResult:
    return ValidationResult(ok=False, errors=errors, warnings=[])


def validate_generated_assets(
    glb_path: Path,
    usdz_path: Path | None,
    *,
    max_glb_bytes: int = 50 * 1024 * 1024,
    min_glb_bytes: int = 0,
    max_usdz_bytes: int = 50 * 1024 * 1024,
) -> ValidationResult:
    """Run the automated checks on a downloaded generation's outputs.

    Checks:
      - GLB exists, size within sane band, valid GLB container header
      - GLB JSON chunk parses (lightweight structural check)
      - USDZ exists, non-empty, within size band (when delivered)

    Deliberately NOT a full glTF validator — texture reference resolution,
    mesh/vertex/bounds checks, and usdchecker stay a clearly isolated
    follow-up rather than destabilizing M2. Human visual review remains
    mandatory and is a separate step.
    """
    errors: list[str] = []

    if not glb_path.exists():
        return _fail(["GLB file missing"])

    size = glb_path.stat().st_size
    if not (min_glb_bytes <= size <= max_glb_bytes):
        errors.append(f"GLB size {size} outside sane range [{min_glb_bytes}, {max_glb_bytes}]")

    glb_errors = _glb_container_errors(glb_path)
    errors.extend(glb_errors)

    if usdz_path is not None:
        if not usdz_path.exists() or usdz_path.stat().st_size <= 0:
            errors.append("USDZ missing or empty")
        elif usdz_path.stat().st_size > max_usdz_bytes:
            errors.append(
                f"USDZ size {usdz_path.stat().st_size} exceeds {max_usdz_bytes}"
            )

    if errors:
        return _fail(errors)
    return _ok()


def _glb_container_errors(path: Path) -> list[str]:
    """Container-level GLB checks: header + first (JSON) chunk.

    Returns a list of error strings; empty means the container looks sane.
    """
    errors: list[str] = []
    try:
        with path.open("rb") as fh:
            header = fh.read(_GLB_HEADER_SIZE)
            if len(header) != _GLB_HEADER_SIZE:
                return ["GLB header truncated"]
            magic, version, declared_length = struct.unpack("<4sII", header)
            if magic != _GLB_MAGIC:
                return ["GLB magic mismatch (not a glTF binary)"]
            if version != 2:
                return [f"Unsupported GLB version {version} (expected 2)"]
            if declared_length < _GLB_HEADER_SIZE:
                return ["GLB declared length smaller than header"]
            actual = path.stat().st_size
            if declared_length != actual:
                errors.append(
                    f"GLB declared length {declared_length} != actual size {actual}"
                )

            # First chunk must be JSON (4-byte length + 4-byte type + data).
            chunk_header = fh.read(_GLB_CHUNK_HEADER_SIZE)
            if len(chunk_header) != _GLB_CHUNK_HEADER_SIZE:
                errors.append("GLB missing first chunk header")
                return errors
            chunk_len, chunk_type = struct.unpack("<I4s", chunk_header)
            if chunk_type != _GLB_CHUNK_TYPE_JSON:
                errors.append("GLB first chunk is not JSON")
                return errors
            json_bytes = fh.read(min(chunk_len, 8 * 1024 * 1024))
            try:
                json.loads(json_bytes)
            except (ValueError, UnicodeDecodeError):
                errors.append("GLB JSON chunk is not valid JSON")
    except OSError as exc:
        errors.append(f"GLB unreadable: {exc}")
    return errors
