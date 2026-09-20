# TRELLIS Colab Worker

This directory contains the **GPU-side** execution environment for the Dscape
Dine AR backend. It runs **only inside the Google Colab T4 environment** and is
deliberately NOT part of the Mac backend package (backend/pyproject.toml).

## Why this is separate

- The Mac backend (backend/.venv, Python 3.11) must **never** import
  torch/TRELLIS/kaolin/xformers.
- TRELLIS needs the verified Colab stack: Python 3.13, PyTorch 2.11.0+cu128,
  CUDA 12.8, Tesla T4.
- The two environments communicate through the **job-directory protocol** in
  `backend/app/providers/trellis_jobs.py` (pure stdlib, shared).

## Files

| File | Purpose |
|---|---|
| `requirements.txt` | Colab-only deps (matches the M4a.1-verified stack) |
| `run_worker.py` | Worker: runs one job (`--once <job_id>`) or a poll loop (`--poll`) |
| `smoke_test.py` | Colab-only GPU smoke test (NOT part of backend pytest) |

## Setup (in Colab, one-time)

```bash
# 1. Isolated env
python -m venv /content/trellis-env

# 2. TRELLIS source at the M4a.1-verified commit
git clone https://github.com/microsoft/TRELLIS.git /content/trellis
cd /content/trellis && git checkout <M4a.1-verified-commit>
/content/trellis-env/bin/pip install -e /content/trellis

# 3. Weights (image-large 1.2B only)
/content/trellis-env/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('microsoft/TRELLIS-image-large', local_dir='/content/trellis/pretrained/trellis-image-large')"
```

## Run

```bash
export TRELLIS_JOB_DIR=/content/trellis_jobs        # shared job directory
export TRELLIS_MODEL_DIR=/content/trellis/pretrained/trellis-image-large

# Smoke test (verifies the exact M4a.1 config)
cd /content/stable-fast-3d/backend/trellis_worker
/content/trellis-env/bin/python smoke_test.py

# Process one job
/content/trellis-env/bin/python run_worker.py --once <job_id>

# Or poll for new jobs
/content/trellis-env/bin/python run_worker.py --poll
```

## Job protocol

```
<trellis_jobs>/<job_id>/request.json   {"image_url": "<stored source image URL>"}
<trellis_jobs>/<job_id>/status.json    PENDING|PROCESSING|SUCCEEDED|FAILED (+progress/error)
<trellis_jobs>/<job_id>/model.glb      output (SUCCEEDED)
<trellis_jobs>/<job_id>/model.usdz     optional
<trellis_jobs>/<job_id>/previews/*.png optional
```

## How the job directory is shared with the Mac backend

The backend provider (`LocalTrellisProvider`) writes `request.json` and reads
`status.json` from `TRELLIS_JOB_DIR`. In the immediate Colab workflow, the Mac
and Colab must share this directory (e.g. the backend's `TRELLIS_JOB_DIR`
points at a synced/mounted volume, or a later transport swaps the client for
network). The transport is isolated in `TrellisJobClient` so nothing else
changes when a persistent connection replaces the shared directory.
