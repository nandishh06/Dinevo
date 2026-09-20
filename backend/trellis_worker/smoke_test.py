"""TRELLIS GPU smoke test — Colab-only, NOT part of the normal backend suite.

Run ONLY inside the Colab T4 environment with /content/trellis-env:

  cd /content/stable-fast-3d/backend/trellis_worker
  /content/trellis-env/bin/python smoke_test.py

It is intentionally excluded from pytest (backend/pyproject.toml testpaths is
"tests", and this lives in trellis_worker/). It verifies the exact M4a.1
configuration before a real job is run.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

DEFAULT_IMAGE = "/content/stable-fast-3d/public/images/dishes/chicken-biryani.jpg"
DEFAULT_MODEL_DIR = "/content/trellis/pretrained/trellis-image-large"


def main() -> int:
    import platform

    print("python:", platform.python_version())
    print("cwd:", Path.cwd())

    try:
        import torch
    except ImportError:
        print("FAIL: torch not installed in this environment")
        return 1
    print("torch:", torch.__version__, "| cuda:", torch.version.cuda)
    if not torch.cuda.is_available():
        print("FAIL: CUDA not available")
        return 1
    print("gpu:", torch.cuda.get_device_name(0))
    total = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)
    print("total VRAM GB:", total)

    from trellis.pipelines import TrellisImageTo3DPipeline
    from PIL import Image

    image_path = os.environ.get("TEST_IMAGE", DEFAULT_IMAGE)
    model_dir = os.environ.get("TRELLIS_MODEL_DIR", DEFAULT_MODEL_DIR)
    print("test image:", image_path, "exists:", Path(image_path).exists())
    print("model dir:", model_dir, "exists:", Path(model_dir).exists())

    t0 = time.time()
    pipeline = TrellisImageTo3DPipeline.from_pretrained(model_dir)
    print("model load s:", round(time.time() - t0, 1))
    print("VRAM after load GB:", round(torch.cuda.memory_allocated() / 1e9, 2))

    image = Image.open(image_path).convert("RGB")
    t1 = time.time()
    outputs = pipeline.run(image, seed=1)
    meshes = outputs["gaussians"].extract_mesh()
    print("inference s:", round(time.time() - t1, 1))
    print("peak VRAM GB:", round(torch.cuda.max_memory_allocated() / 1e9, 2))

    out = Path(os.environ.get("OUTPUT_DIR", "/content/trellis-smoke"))
    out.mkdir(parents=True, exist_ok=True)
    glb = out / "smoke.glb"
    meshes.export(str(glb))
    print("GLB:", glb, "size:", glb.stat().st_size)

    try:
        import trimesh

        m = trimesh.load(str(glb))
        geoms = list(m.geometry.values()) if isinstance(m, trimesh.Scene) else [m]
        verts = sum(len(g.vertices) for g in geoms if hasattr(g, "vertices"))
        faces = sum(len(g.faces) for g in geoms if hasattr(g, "faces"))
        print("vertices:", verts, "triangles:", faces)
    except Exception as exc:  # noqa: BLE001
        print("WARN: trimesh inspection failed:", exc)

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
