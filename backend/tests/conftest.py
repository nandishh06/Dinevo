"""Shared test fixtures: fake provider and GLB test helpers."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from app.providers.base import (
    ImageTo3DProvider,
    ProviderAsset,
    ProviderTaskStatus,
)


def make_glb_bytes() -> bytes:
    """A minimal but structurally valid GLB v2 container.

    Header (12 bytes) + one JSON chunk ("{}") + optional BIN chunk. This is
    valid enough for the container-level validation in this milestone.
    """
    json_chunk = b"{}"
    json_chunk_padded = json_chunk + b" " * ((4 - len(json_chunk) % 4) % 4)
    bin_chunk = b"0123456789"  # 10 bytes -> padded to 12
    bin_chunk_padded = bin_chunk + b" " * ((4 - len(bin_chunk) % 4) % 4)
    total = (
        12
        + 8
        + len(json_chunk_padded)
        + 8
        + len(bin_chunk_padded)
    )
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(json_chunk_padded), b"JSON")
        + json_chunk_padded
        + struct.pack("<I4s", len(bin_chunk_padded), b"BIN\x00")
        + bin_chunk_padded
    )


def make_real_glb_bytes() -> bytes:
    """A GLB with a JSON chunk that describes a minimal but parseable scene
    (one node, no mesh). Valid for JSON-parse validation and container checks."""
    gltf = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "dish"}],
    }
    payload = json.dumps(gltf).encode()
    padded = payload + b" " * ((4 - len(payload) % 4) % 4)
    total = 12 + 8 + len(padded)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(padded), b"JSON")
        + padded
    )


class FakeImageTo3DProvider(ImageTo3DProvider):
    """Deterministic fake provider. No network access."""

    name = "fake"

    def __init__(self) -> None:
        self.submitted: list[str] = []
        self.poll_results: list[ProviderTaskStatus] = [
            ProviderTaskStatus(status="SUCCEEDED", progress=100)
        ]
        self.assets: ProviderAsset | None = ProviderAsset(
            glb_url="https://provider.test/dish.glb",
            usdz_url="https://provider.test/dish.usdz",
            preview_urls={
                "front": "https://provider.test/preview_front.png",
                "right": "https://provider.test/preview_right.png",
            },
        )
        self.fail_poll: bool = False
        self.poll_error: str = "provider exploded"

    def submit(self, image_url: str) -> str:
        self.submitted.append(image_url)
        return "fake_task_123"

    def poll(self, task_id: str) -> ProviderTaskStatus:
        if self.fail_poll:
            return ProviderTaskStatus(
                status="FAILED", progress=50, error=self.poll_error
            )
        return self.poll_results[0]

    def fetch_assets(self, task_id: str) -> ProviderAsset:
        if self.assets is None:
            raise RuntimeError("no assets")
        return self.assets


@pytest.fixture()
def fake_provider() -> FakeImageTo3DProvider:
    return FakeImageTo3DProvider()


class FakeAssetServer:
    """Serves fake GLB/USDZ/preview bytes over real HTTP so the service's
    _download() has genuine URLs to fetch (no provider network involved)."""

    def __init__(self, tmp_path: Path) -> None:
        self._dir = tmp_path / "fake-provider-assets"
        self._dir.mkdir(parents=True, exist_ok=True)
        self.glb = self._write("model.glb", make_real_glb_bytes())
        self.usdz = self._write("model.usdz", b"USDPackage-bytes")
        self.preview_front = self._write("preview_front.png", b"png-bytes")
        self.preview_right = self._write("preview_right.png", b"png-bytes")

    def _write(self, name: str, data: bytes) -> Path:
        p = self._dir / name
        p.write_bytes(data)
        return p

    def url(self, path: Path) -> str:
        return path.as_uri()


@pytest.fixture()
def fake_asset_server(tmp_path: Path) -> FakeAssetServer:
    return FakeAssetServer(tmp_path)
