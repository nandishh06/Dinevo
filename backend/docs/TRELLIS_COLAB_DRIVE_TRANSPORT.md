# TRELLIS Colab ↔ Mac Drive Transport (development bridge)

Zero-cost bridge for the ONE-dish real proof. The Mac backend and the Colab T4
do **not** share a filesystem directly; Google Drive is the temporary $0
shared folder both sides can read/write.

## Design

```
Mac backend (data/trellis_jobs/)
  staging/<job_id>/request.json + status.json(PENDING)     <- provider.submit()
        │  (rclone/Drive Desktop syncs staging/ → Drive folder)
        ▼
Drive folder (shared, e.g. "MyDrive/trellis-jobs")
        │  (Colab mounts Drive at /content/drive)
        ▼
Colab worker polls /content/drive/MyDrive/trellis-jobs/*/request.json
  runs TRELLIS image-large on T4
  writes status.json(PROCESSING→SUCCEEDED/FAILED) + model.glb/model.usdz
        │  (results sync back from Drive folder → results/)
        ▼
Mac backend (data/trellis_jobs/)
  results/<job_id>/...                                    <- provider.poll/fetch_assets
```

`TrellisJobClient` (backend) is unchanged in its public API — the transport
now uses `staging/` for submit and `results/` (falling back to `staging/`) for
poll/fetch. The Colab worker writes back into the **same job dir** it read.

## Colab setup (copy-paste into a Colab cell, T4 runtime)

```python
# 1. Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# 2. Verify the shared folder exists (create it in Drive if missing):
#    MyDrive/trellis-jobs
import os
JOBS = "/content/drive/MyDrive/trellis-jobs"
os.makedirs(JOBS, exist_ok=True)
print("jobs dir:", JOBS, "exists:", os.path.exists(JOBS))
```

```python
# 3. Clone the project + set up trellis-env (one-time, M4a.1-verified stack)
!git clone https://github.com/microsoft/TRELLIS.git /content/trellis
#   ... or if /content/trellis already exists at the M4a.1 commit, skip.
#   Create the venv + install TRELLIS per backend/trellis_worker/README.md
#   Download TRELLIS image-large weights (microsoft/TRELLIS-image-large)
```

```python
# 4. Run the worker, polling the DRIVE folder (not /content/trellis_jobs)
import os, sys
os.environ["TRELLIS_JOB_DIR"] = "/content/drive/MyDrive/trellis-jobs"
os.environ["TRELLIS_MODEL_DIR"] = "/content/trellis/pretrained/trellis-image-large"
# Copy the worker to a location that can import app.providers.trellis_jobs,
# or add the repo to sys.path:
sys.path.insert(0, "/content/stable-fast-3d")
!cd /content/stable-fast-3d/backend && /content/trellis-env/bin/python trellis_worker/run_worker.py --poll --job-root "/content/drive/MyDrive/trellis-jobs"
```

> The worker writes `status.json` + `model.glb` into the job dir it found on
> Drive. Drive sync propagates it back to the Mac (Drive Desktop/rclone).

## Mac side (copy-paste)

```bash
# In backend/.env (or env):
export IMAGE_TO_3D_PROVIDER=trellis
export TRELLIS_JOB_DIR=./data/trellis_jobs          # staging/ + results/
# Bridge the shared folder. Two $0 options:
#   Option A: Google Drive Desktop on the Mac -> symlink the Drive folder:
#     ln -s ~/Library/CloudStorage/GoogleDrive-*/MyDrive/trellis-jobs backend/data/trellis_jobs/bridge
#   Option B: rclone (free) mount:
#     rclone mount gdrive:trellis-jobs backend/data/trellis_jobs/bridge
```

The Mac sync step (run after each submit, or as a tiny loop):

```bash
# Move staged jobs OUT to the Drive bridge, and completed jobs IN to results/:
rsync -av backend/data/trellis_jobs/staging/ backend/data/trellis_jobs/bridge/out/
rsync -av backend/data/trellis_jobs/bridge/in/ backend/data/trellis_jobs/results/
```

> The exact sync tool is a **user/ops decision** (Drive Desktop is simplest
> if installed; rclone needs no account beyond the existing Google login).
> No credentials are stored in the repo — Drive auth is the user's browser
> session or an rclone config in `~/.config/rclone` (never committed).

## Race-condition note

Drive sync latency is seconds-to-minutes. For the ONE-dish proof this is
fine: the worker polls every 10s and the generation takes minutes. The
provider's `poll()` returns the current `status.json`; the generation flow is
bounded so it will not hang forever if sync stalls. Do NOT use this for
high-throughput production.

## Security

- No Google credentials, tokens, or provider API keys in the repo.
- Drive auth stays in the user's browser session / rclone config (outside the
  repo).
- The shared folder is private to the user's own Google account.
