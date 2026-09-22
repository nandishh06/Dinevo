"""TRELLIS Colab worker — runs GPU image->3D jobs for the Dscape backend.

Runs ONLY in the Colab T4 environment.

Job protocol:

  <TRELLIS_JOB_DIR>/<job_id>/request.json
      -> source image URL + optional generation params

  <TRELLIS_JOB_DIR>/<job_id>/status.json
      -> PENDING / PROCESSING / SUCCEEDED / FAILED

  <TRELLIS_JOB_DIR>/<job_id>/model.glb
      -> generated GLB

  <TRELLIS_JOB_DIR>/<job_id>/model.usdz
      -> optional USDZ

Usage inside Colab:

  /content/trellis-env/bin/python run_worker.py --once <JOB_ID>

  /content/trellis-env/bin/python run_worker.py --poll

Environment:

  TRELLIS_JOB_DIR
      Default: /content/trellis_jobs

  TRELLIS_MODEL_DIR
      Default:
      /content/trellis/pretrained/trellis-image-large

This worker runs TRELLIS only.
It does not call any paid generation API.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

JOB_ROOT_ENV = "TRELLIS_JOB_DIR"
DEFAULT_JOB_ROOT = "/content/trellis_jobs"

MODEL_DIR_ENV = "TRELLIS_MODEL_DIR"
DEFAULT_MODEL_DIR = "/content/trellis/pretrained/trellis-image-large"

POLL_INTERVAL_SECONDS = 10


# ============================================================
# TRELLIS IMPORT
# ============================================================

def _import_trellis():
    """
    Import heavy GPU dependencies lazily.

    This function is only called inside the Colab GPU worker.
    """

    import torch

    from trellis.pipelines import TrellisImageTo3DPipeline

    return torch, TrellisImageTo3DPipeline


# ============================================================
# STATUS
# ============================================================

def _set_status(
    job_dir: Path,
    status: str,
    progress: int,
    error: str | None = None,
) -> None:
    """
    Write the current job status atomically.
    """

    job_dir.mkdir(parents=True, exist_ok=True)

    status_file = job_dir / "status.json"
    temp_file = job_dir / "status.json.tmp"

    payload = {
        "status": status,
        "progress": progress,
        "error": error,
    }

    temp_file.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    temp_file.replace(status_file)


# ============================================================
# REQUEST LOADING
# ============================================================

def _load_request(job_dir: Path) -> dict:
    """
    Load and validate request.json.
    """

    request_file = job_dir / "request.json"

    if not request_file.exists():
        raise FileNotFoundError(
            f"Missing request.json: {request_file}"
        )

    try:
        request = json.loads(
            request_file.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid request.json: {exc}"
        ) from exc

    if not isinstance(request, dict):
        raise RuntimeError(
            "request.json must contain a JSON object"
        )

    return request


# ============================================================
# IMAGE FETCHING
# ============================================================

def _fetch_source_image(
    image_url: str,
    destination: Path,
) -> None:
    """
    Download the source image.

    Preferred path:
        Dscape's shared TrellisJobClient.

    Fallback:
        Direct HTTP download.

    The fallback makes the Colab worker less dependent on the
    Mac backend Python package being installed in Colab.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # First try the shared Dscape job client.
    # --------------------------------------------------------

    try:
        from app.providers.trellis_jobs import TrellisJobClient

        print("[IMAGE] Using TrellisJobClient")

        TrellisJobClient.fetch_image_to_local(
            image_url,
            destination,
        )

        if destination.exists() and destination.stat().st_size > 0:
            return

    except Exception as exc:
        print(
            "[IMAGE] TrellisJobClient unavailable/failed: "
            f"{exc}"
        )

    # --------------------------------------------------------
    # Fallback to HTTP.
    # --------------------------------------------------------

    if not image_url.startswith(("http://", "https://")):
        raise RuntimeError(
            "Cannot fetch source image. "
            "image_url is not an HTTP/HTTPS URL and "
            "TrellisJobClient was unavailable."
        )

    print("[IMAGE] Using direct HTTP download")

    try:
        import urllib.request

        urllib.request.urlretrieve(
            image_url,
            destination,
        )

    except Exception as exc:
        raise RuntimeError(
            f"Failed to download source image: {exc}"
        ) from exc

    if not destination.exists():
        raise RuntimeError(
            "Image download completed but source file "
            "does not exist."
        )

    if destination.stat().st_size == 0:
        raise RuntimeError(
            "Downloaded source image is empty."
        )


# ============================================================
# PIPELINE LOADING
# ============================================================

def _load_pipeline(model_dir: str):
    """
    Load TRELLIS once.

    Keeping the pipeline alive is important for --poll mode.
    Otherwise every job would reload all model weights.
    """

    torch, TrellisImageTo3DPipeline = _import_trellis()

    print()
    print("=" * 70)
    print("TRELLIS GPU ENVIRONMENT")
    print("=" * 70)

    print("PyTorch:", torch.__version__)
    print("CUDA:", torch.version.cuda)

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available."
        )

    gpu_name = torch.cuda.get_device_name(0)

    total_vram_gb = (
        torch.cuda.get_device_properties(0).total_memory
        / 1024**3
    )

    print("GPU:", gpu_name)
    print(f"VRAM: {total_vram_gb:.2f} GB")

    print()
    print("Model directory:")
    print(model_dir)

    if not os.path.exists(model_dir):
        raise FileNotFoundError(
            f"TRELLIS model directory does not exist: "
            f"{model_dir}"
        )

    print()
    print("Loading TRELLIS pipeline...")

    pipeline = TrellisImageTo3DPipeline.from_pretrained(
        model_dir
    )

    print("TRELLIS pipeline: READY")

    return torch, pipeline


# ============================================================
# MESH EXTRACTION
# ============================================================

def _extract_mesh(outputs):
    """
    Extract a mesh from the actual TRELLIS output.

    Your verified TRELLIS installation returns:

        mesh
        gaussian
        radiance_field

    Therefore 'mesh' is preferred.

    'gaussian' is retained as a compatibility fallback.
    """

    output_keys = list(outputs.keys())

    print(
        "[TRELLIS] Output keys:",
        output_keys,
    )

    # --------------------------------------------------------
    # Preferred path: direct mesh
    # --------------------------------------------------------

    if "mesh" in outputs:

        print(
            "[TRELLIS] Using direct mesh output"
        )

        mesh = outputs["mesh"]

        if mesh is None:
            raise RuntimeError(
                "TRELLIS returned mesh=None"
            )

        return mesh

    # --------------------------------------------------------
    # Compatibility path: Gaussian -> mesh
    # --------------------------------------------------------

    if "gaussian" in outputs:

        print(
            "[TRELLIS] Extracting mesh from gaussian output"
        )

        gaussian = outputs["gaussian"]

        if gaussian is None:
            raise RuntimeError(
                "TRELLIS returned gaussian=None"
            )

        if not hasattr(gaussian, "extract_mesh"):
            raise RuntimeError(
                "Gaussian output does not provide "
                "extract_mesh()."
            )

        return gaussian.extract_mesh()

    # --------------------------------------------------------
    # Nothing usable
    # --------------------------------------------------------

    raise RuntimeError(
        "TRELLIS produced no usable mesh output. "
        f"Available keys: {output_keys}"
    )


# ============================================================
# GLB EXPORT
# ============================================================

def _export_glb(mesh, glb_path: Path) -> None:
    """
    Export the generated mesh as GLB.
    """

    glb_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "[GLB] Exporting:",
        glb_path,
    )

    if not hasattr(mesh, "export"):
        raise RuntimeError(
            "TRELLIS mesh object does not provide export()."
        )

    mesh.export(
        str(glb_path)
    )

    if not glb_path.exists():
        raise RuntimeError(
            "Mesh export returned without creating "
            f"{glb_path}"
        )

    file_size_mb = (
        glb_path.stat().st_size
        / 1024
        / 1024
    )

    if file_size_mb <= 0:
        raise RuntimeError(
            "Generated GLB is empty."
        )

    print(
        f"[GLB] Created: {file_size_mb:.2f} MB"
    )


# ============================================================
# OPTIONAL USDZ
# ============================================================

def _export_usdz(mesh, usdz_path: Path) -> None:
    """
    Attempt USDZ export.

    USDZ is optional. Failure does NOT fail the job.
    """

    try:

        print(
            "[USDZ] Attempting export..."
        )

        mesh.export(
            str(usdz_path)
        )

        if usdz_path.exists():

            file_size_mb = (
                usdz_path.stat().st_size
                / 1024
                / 1024
            )

            print(
                f"[USDZ] Created: "
                f"{file_size_mb:.2f} MB"
            )

        else:

            print(
                "[USDZ] Export returned but "
                "file was not created."
            )

    except Exception as exc:

        print(
            "[USDZ] Optional export skipped:",
            exc,
        )


# ============================================================
# RUN ONE JOB
# ============================================================

def run_job(
    job_id: str,
    job_root: Path,
    pipeline,
) -> bool:

    """
    Execute one TRELLIS generation job.

    Returns:
        True  -> successful
        False -> failed
    """

    job_dir = job_root / job_id

    print()
    print("=" * 70)
    print(f"TRELLIS JOB: {job_id}")
    print("=" * 70)

    # --------------------------------------------------------
    # Check job directory
    # --------------------------------------------------------

    if not job_dir.exists():

        print(
            f"[{job_id}] ERROR: job directory does not exist:"
        )
        print(job_dir)

        return False

    try:

        # ----------------------------------------------------
        # Load request
        # ----------------------------------------------------

        request = _load_request(
            job_dir
        )

        image_url = request.get(
            "image_url"
        )

        if not image_url:

            raise RuntimeError(
                "request.json does not contain image_url"
            )

        print(
            f"[{job_id}] image_url={image_url}"
        )

        _set_status(
            job_dir,
            "PROCESSING",
            5,
            None,
        )

        # ----------------------------------------------------
        # Download image
        # ----------------------------------------------------

        source = (
            job_dir
            / "source.jpg"
        )

        print(
            f"[{job_id}] Fetching source image..."
        )

        _fetch_source_image(
            image_url,
            source,
        )

        print(
            f"[{job_id}] Source image:"
            f" {source}"
        )

        # ----------------------------------------------------
        # Open image
        # ----------------------------------------------------

        from PIL import Image

        image = Image.open(
            source
        ).convert("RGB")

        print(
            f"[{job_id}] Image size:"
            f" {image.size}"
        )

        _set_status(
            job_dir,
            "PROCESSING",
            40,
            None,
        )

        # ----------------------------------------------------
        # TRELLIS inference
        # ----------------------------------------------------

        print()
        print(
            f"[{job_id}] Starting TRELLIS inference..."
        )

        # Keep generation parameters explicit.
        #
        # These are the same basic parameters used during
        # the successful T4 inference test.

        outputs = pipeline.run(
            image,
            seed=1,
        )

        print(
            f"[{job_id}] TRELLIS inference complete"
        )

        _set_status(
            job_dir,
            "PROCESSING",
            70,
            None,
        )

        # ----------------------------------------------------
        # Extract mesh
        # ----------------------------------------------------

        mesh = _extract_mesh(
            outputs
        )

        _set_status(
            job_dir,
            "PROCESSING",
            80,
            None,
        )

        # ----------------------------------------------------
        # Export GLB
        # ----------------------------------------------------

        glb_path = (
            job_dir
            / "model.glb"
        )

        _export_glb(
            mesh,
            glb_path,
        )

        # ----------------------------------------------------
        # Optional USDZ
        # ----------------------------------------------------

        usdz_path = (
            job_dir
            / "model.usdz"
        )

        _export_usdz(
            mesh,
            usdz_path,
        )

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------

        _set_status(
            job_dir,
            "SUCCEEDED",
            100,
            None,
        )

        print()
        print(
            "=" * 70
        )
        print(
            f"[{job_id}] SUCCEEDED"
        )
        print(
            f"[{job_id}] GLB: {glb_path}"
        )
        print(
            "=" * 70
        )

        return True

    except Exception as exc:

        error_message = (
            f"{type(exc).__name__}: {exc}"
        )

        print()
        print(
            "=" * 70
        )
        print(
            f"[{job_id}] FAILED"
        )
        print(
            error_message
        )
        print(
            "=" * 70
        )

        try:

            _set_status(
                job_dir,
                "FAILED",
                100,
                error_message[:1000],
            )

        except Exception as status_exc:

            print(
                f"[{job_id}] Could not write "
                f"failure status: {status_exc}"
            )

        return False


# ============================================================
# POLL MODE
# ============================================================

def poll_jobs(
    job_root: Path,
    pipeline,
) -> None:

    """
    Continuously poll the shared job directory.
    """

    print()
    print("=" * 70)
    print("TRELLIS WORKER POLLING")
    print("=" * 70)
    print(
        f"Job root: {job_root}"
    )
    print(
        f"Poll interval: "
        f"{POLL_INTERVAL_SECONDS}s"
    )
    print(
        "Waiting for PENDING jobs..."
    )
    print("=" * 70)

    while True:

        try:

            request_files = sorted(
                job_root.glob(
                    "*/request.json"
                )
            )

            for request_file in request_files:

                job_dir = (
                    request_file.parent
                )

                status_file = (
                    job_dir
                    / "status.json"
                )

                status = "PENDING"

                if status_file.exists():

                    try:

                        status_data = json.loads(
                            status_file.read_text(
                                encoding="utf-8"
                            )
                        )

                        status = status_data.get(
                            "status",
                            "PENDING",
                        )

                    except (
                        ValueError,
                        json.JSONDecodeError,
                    ):

                        print(
                            f"[{job_dir.name}] "
                            "WARNING: invalid status.json; "
                            "treating as PENDING"
                        )

                        status = "PENDING"

                # ------------------------------------------------
                # Only process pending jobs.
                #
                # FAILED jobs are intentionally retried.
                # ------------------------------------------------

                if status in (
                    "PENDING",
                    "FAILED",
                ):

                    print()
                    print(
                        f"[WORKER] Found job "
                        f"{job_dir.name} "
                        f"status={status}"
                    )

                    run_job(
                        job_dir.name,
                        job_root,
                        pipeline,
                    )

        except KeyboardInterrupt:

            print()
            print(
                "TRELLIS worker stopped."
            )

            return

        except Exception as exc:

            print(
                "[WORKER] Polling error:",
                f"{type(exc).__name__}: {exc}",
            )

        time.sleep(
            POLL_INTERVAL_SECONDS
        )


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "TRELLIS Colab GPU worker "
            "(one job or polling mode)"
        )
    )

    group = (
        parser
        .add_mutually_exclusive_group(
            required=True
        )
    )

    group.add_argument(
        "--once",
        metavar="JOB_ID",
        help=(
            "Run a single TRELLIS job "
            "and exit."
        ),
    )

    group.add_argument(
        "--poll",
        action="store_true",
        help=(
            "Continuously poll for "
            "TRELLIS jobs."
        ),
    )

    parser.add_argument(
        "--job-root",
        default=os.environ.get(
            JOB_ROOT_ENV,
            DEFAULT_JOB_ROOT,
        ),
        help=(
            "Shared TRELLIS job directory."
        ),
    )

    parser.add_argument(
        "--model-dir",
        default=os.environ.get(
            MODEL_DIR_ENV,
            DEFAULT_MODEL_DIR,
        ),
        help=(
            "TRELLIS pretrained model directory."
        ),
    )

    args = parser.parse_args()

    job_root = Path(
        args.job_root
    )

    job_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 70)
    print("Dscape TRELLIS WORKER")
    print("=" * 70)
    print(
        "Job root:",
        job_root,
    )
    print(
        "Model dir:",
        args.model_dir,
    )
    print("=" * 70)

    # --------------------------------------------------------
    # Load TRELLIS ONCE
    # --------------------------------------------------------

    try:

        torch, pipeline = _load_pipeline(
            args.model_dir
        )

    except Exception as exc:

        print()
        print(
            "=" * 70
        )
        print(
            "TRELLIS PIPELINE LOAD FAILED"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        print(
            "=" * 70
        )

        return 1

    # --------------------------------------------------------
    # Single-job mode
    # --------------------------------------------------------

    if args.once:

        success = run_job(
            args.once,
            job_root,
            pipeline,
        )

        return 0 if success else 1

    # --------------------------------------------------------
    # Polling mode
    # --------------------------------------------------------

    poll_jobs(
        job_root,
        pipeline,
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    sys.exit(
        main()
    )