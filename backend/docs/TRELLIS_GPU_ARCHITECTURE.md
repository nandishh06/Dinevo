# TRELLIS GPU Architecture

The $0 local image→3D pipeline: the Mac backend stays GPU-free; TRELLIS runs
in the Colab T4 laboratory; the two communicate through a clean job boundary.

```
Hotel Admin
  ↓ upload image
POST /admin/dishes/{id}/image
  ↓ stored via AssetStorage (originals/<dish_id>/...)
POST /admin/dishes/{id}/3d-assets
  ↓ Generation(PENDING) → background worker
GenerationService.run()
  ↓
ImageTo3DProvider
  ↓
LocalTrellisProvider ────── job directory (TRELLIS_JOB_DIR) ──────► Colab TRELLIS worker
  ↓ request.json / status.json                                     (backend/trellis_worker/run_worker.py)
  ↓ model.glb / model.usdz / previews                              TRELLIS image-large 1.2B on T4
  ↓
download → validate → AssetStorage
  ↓
READY_FOR_REVIEW
  ↓ admin approval (POST /admin/generations/{id}/approve)
PUBLISHED → Dish.model_url
  ↓
existing customer 3D/WebAR frontend (unchanged)
```

## A. Mac development environment (canonical)

- `backend/.venv` (Python 3.11): FastAPI + SQLAlchemy + pytest only.
- **No** torch / CUDA / TRELLIS / kaolin / xformers — intentionally.
- Runs: frontend, FastAPI, database, asset API, admin API, tests.
- Provider selection via `IMAGE_TO_3D_PROVIDER` (`meshy` default | `trellis`).

## B. Colab GPU environment (temporary laboratory)

- Python 3.13, PyTorch 2.11.0+cu128, CUDA 12.8, Tesla T4 (14.56 GB VRAM).
- Isolated env at `/content/trellis-env`; TRELLIS source at `/content/trellis`
  at the M4a.1-verified commit; weights `microsoft/TRELLIS-image-large` (1.2B).
- See `backend/trellis_worker/README.md` for exact setup.

## C. TRELLIS worker setup

```bash
# Colab only
python -m venv /content/trellis-env
git clone https://github.com/microsoft/TRELLIS.git /content/trellis
cd /content/trellis && git checkout <M4a.1-verified-commit>
/content/trellis-env/bin/pip install -e /content/trellis
/content/trellis-env/bin/python -c \
  "from huggingface_hub import snapshot_download; \
   snapshot_download('microsoft/TRELLIS-image-large', \
   local_dir='/content/trellis/pretrained/trellis-image-large')"
export TRELLIS_JOB_DIR=/content/trellis_jobs
export TRELLIS_MODEL_DIR=/content/trellis/pretrained/trellis-image-large
/content/trellis-env/bin/python /content/stable-fast-3d/backend/trellis_worker/smoke_test.py
/content/trellis-env/bin/python /content/stable-fast-3d/backend/trellis_worker/run_worker.py --poll
```

## D. How a generation job flows

1. Admin uploads an image → `DishService.store_dish_image` → AssetStorage
   (`originals/<dish_id>/...`) → `Dish.image_url`.
2. `POST /admin/dishes/{id}/3d-assets` validates the dish has a source image,
   creates `Generation(PENDING)`, schedules the background worker.
3. Worker → `GenerationService.run()` → `LocalTrellisProvider.submit(image_url)`
   writes `<TRELLIS_JOB_DIR>/<job_id>/request.json`.
4. Colab worker picks up the job, downloads the stored source image, runs
   TRELLIS image-large, writes `status.json` (PROCESSING → SUCCEEDED/FAILED)
   and `model.glb` (+ optional `model.usdz`, previews).
5. Provider `poll()` reads status; `fetch_assets()` returns the GLB/USDZ
   URLs. `GenerationService` downloads, validates, stores via AssetStorage,
   and marks `READY_FOR_REVIEW` (or `FAILED`).
6. Nothing publishes automatically.

## E. Reviewing generated assets

`GET /admin/generations/{id}` exposes status + GLB/USDZ/preview URLs. The
admin (human quality gate) inspects the model, then approves.

## F. How approval publishes model_url

`POST /admin/generations/{id}/approve` — the ONLY operation that writes
`Dish.model_url`. Approval transitions APPROVED → PUBLISHED and copies the
stored GLB URL to the dish; the customer 3D/WebAR UI then shows it.

## G. Running backend tests without a GPU

```bash
cd backend
.venv/bin/python -m pytest          # 60+ tests, all fake-provider, no CUDA
.venv/bin/python -m py_compile $(find app tests -name '*.py')
```

## H. Running the GPU smoke test (Colab only)

```bash
cd /content/stable-fast-3d/backend/trellis_worker
/content/trellis-env/bin/python smoke_test.py
```

This is intentionally NOT part of the normal backend suite (it lives in
`backend/trellis_worker/`, outside pytest `testpaths`).

## Transport note

`TrellisJobClient` (backend side) and `run_worker.py` (Colab side) share the
pure-stdlib job-directory protocol in `app/providers/trellis_jobs.py`. The
immediate transport is a shared directory (mounted/synced). Replacing it with
a network transport only swaps the client implementation — the provider,
GenerationService, and lifecycle do not change.
