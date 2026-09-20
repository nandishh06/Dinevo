# Dinevo Dine AR — Project Overview & Working Playbook

> A QR-driven hotel and restaurant menu where a photographed dish becomes a
> real 3D model a guest can rotate on screen and place on their own table in
> AR — generated for **zero cost** by our own open-source pipeline.

---

## 1. What We Are Building

**The product in one sentence:** a guest scans a printed QR code on their
table, opens the restaurant menu, browses real dish photography, and can
view any dish as a 3D model — in a viewer or placed on their own table
through the camera.

**The three acts of the product:**

| Act | Who | What happens |
|---|---|---|
| **Create** | Hotel / restaurant admin | Uploads a real photo of a dish |
| **Generate** | Our backend + GPU worker | Turns the photo into a 3D model (GLB/USDZ) |
| **Experience** | The guest at the table | Scans QR, browses, views the dish in 3D / AR |

The whole point: **a restaurant does not need a 3D artist or a paid 3D
service.** A chef's photo goes in, a guest-ready 3D dish comes out.

---

## 2. The Humanised Journey

Follow one dish — **Chicken Biryani** — from the kitchen to the table.

```
 1. THE PHOTO                The restaurant takes a top-down photo of the
                             plated biryani. That is the only input we need.

 2. THE UPLOAD               An admin adds the dish in the back office and
                             uploads the photo. The backend stores it safely.

 3. THE WAIT                 A generation job is created (PENDING). Nobody
                             stares at a loading bar — the work happens in
                             the background.

 4. THE MAGIC                A GPU worker (TRELLIS, an open-source model)
                             reconstructs the dish as a 3D mesh — rice,
                             chicken, bowl — with the photo as its texture.

 5. THE CHECK                The model lands in "Ready for review". A human
                             looks at it. If it looks like food and not an
                             alien, it is approved.

 6. THE PUBLISH              Approval publishes the model to the dish. The
                             menu now advertises a real 3D preview.

 7. THE GUEST                A guest scans the QR, opens the dish, taps
                             "View 3D" — or points the camera at the table
                             and places the biryani in their space in AR.
```

> The human quality gate is sacred: **a generated model is never published
> automatically.** A person always decides whether the dish looks like a dish.

---

## 3. The Previous Architecture (Phase 1 — M1 → M3)

Before the GPU work, the project had a complete **customer-facing** flow and
a **mock-backed backend** with a documented seam for a future generation
service.

```
PHASE 1 (built, working)

  Guest:  QR → /t/$token → menu → dish detail → 3D/AR (model-viewer)

  Backend (M1→M3):
    FastAPI + SQLAlchemy (SQLite dev)
    ├── Dish, Generation models + lifecycle
    │     PENDING → PROCESSING → READY_FOR_REVIEW → APPROVED → PUBLISHED
    ├── GenerationService        (orchestrates the lifecycle)
    ├── ImageTo3DProvider (ABC)  (the provider boundary)
    │     └── MeshyProvider      (paid cloud API)
    ├── AssetStorage (ABC)       (where generated files live)
    │     └── LocalAssetStorage  (local disk, dev)
    ├── Validation foundation
    └── Admin API: create dish, upload image, start generation,
        get status, approve
```

**What Phase 1 had:**
- A polished guest menu + AR experience (`DishARViewer`, `CameraArView`,
  lazy-loaded `model-viewer`).
- One real hand-crafted model (`chicken-biryani.glb` + `.usdz`).
- A complete backend lifecycle with tests (45 at end of M3, 65 now).
- Mock data behind a single API seam (`src/lib/api/`).

**What Phase 1 lacked:**
- A real, affordable way to turn an uploaded photo into a 3D model.
- `MeshyProvider` existed but required a **paid API key and credits** — which
  conflicts with the project's $0 requirement.
- Only 1 of 15 dishes had any 3D asset (`paneer-tikka` and `masala-dosa` are
  referenced in the menu but have no model file — they silently fall back to
  photo-only AR).

---

## 4. What Is Changing (M4 — the $0 generation pipeline)

### The decision

> The project must run on a **$0 / free-tier basis**. No paid 3D APIs, no
> credits, no paid GPU services.

This ruled out Meshy (and the SF3D experiment, which ran out of GPU memory on
the T4). After evaluating open-source image-to-3D models, we chose
**TRELLIS image-large (1.2B)** — MIT-licensed, free weights, runs on our
Tesla T4, outputs GLB directly.

### The architecture change

The existing `ImageTo3DProvider` boundary stays exactly as designed. We add a
second implementation and split execution across two machines:

```
BEFORE (M1–M3)                          AFTER (M4)

  FastAPI                                  FastAPI (Mac)
    └─ GenerationService                     └─ GenerationService
         └─ MeshyProvider (paid)                  └─ LocalTrellisProvider   NEW
              └─ Meshy cloud                          └─ Job protocol (staging/results)
                                                          └─ Google Drive bridge   $0
                                                              └─ Colab T4 worker   NEW
                                                                   └─ TRELLIS image-large
                                                                        └─ GLB/USDZ
```

**What stays the same:**
- `GenerationService`, the lifecycle, `AssetStorage`, validation, the admin
  API, and the entire customer AR frontend.
- `MeshyProvider` remains in the codebase (behind the same ABC) but is not
  used by the $0 path.

**What is new:**
- `LocalTrellisProvider` — a provider that never touches torch/TRELLIS on
  the Mac; it speaks the job protocol.
- `trellis_jobs.py` — a pure-stdlib job-directory protocol
  (`staging/<job_id>/` → worker → `results/<job_id>/`).
- `backend/trellis_worker/` — the Colab-side worker (`run_worker.py`) and a
  GPU smoke test, isolated from the Mac backend.
- The **Drive bridge** — Google Drive as the temporary $0 shared folder.
- A **cloudflared quick tunnel** so Colab can fetch the uploaded photo from
  the Mac backend over HTTPS.

### Environment split (important to internalise)

| | Mac + VS Code | Google Colab (Chrome) |
|---|---|---|
| Role | Canonical application | Temporary GPU laboratory |
| Runs | Frontend, FastAPI, DB, asset API, admin API, tests | TRELLIS worker, T4 GPU |
| GPU | None (Intel + AMD, no CUDA) | Tesla T4, 14.56 GB VRAM |
| Python | 3.11 (backend/.venv) | 3.13 (`/content/trellis-env`) |
| Heavy deps | **Never** torch/TRELLIS/kaolin | torch 2.11.0+cu128, TRELLIS |

The two sides communicate **only** through the job protocol — the Mac never
imports a GPU library, and Colab never touches the database.

---

## 5. The End-to-End Workflow (current, M4a.3)

```
HOTEL ADMIN (Mac browser)              GPU LAB (Colab T4)               GUEST
──────────────────────                 ────────────────                 ─────
 1. Upload dish photo
    POST /admin/dishes/{id}/image
    → stored via AssetStorage
    → public HTTPS URL (cloudflared)
        │
 2. Start generation
    POST /admin/dishes/{id}/3d-assets
    → Generation(PENDING)
    → job written to staging/<job_id>/
        │
 3. ── Drive bridge ─────────────────► 4. Worker polls Drive folder
                                          finds request.json
                                          downloads photo (HTTPS)
                                          runs TRELLIS image-large
                                          writes status.json + model.glb
                                          (PROCESSING → SUCCEEDED)
        ◄─────────────── Drive sync ────
 5. Job appears in results/<job_id>/
    GenerationService fetches, validates,
    stores via AssetStorage
    → READY_FOR_REVIEW
        │
 6. Admin inspects the model (human gate)
    POST /admin/generations/{id}/approve
    → APPROVED → PUBLISHED
    → Dish.model_url = generated GLB
        │
 7. Guest scans QR → dish detail
    → "View 3D" / "View in AR"
    → model-viewer loads the published GLB
```

### Generation lifecycle

```
PENDING ──► PROCESSING ──► READY_FOR_REVIEW ──► APPROVED ──► PUBLISHED
                │                │
                ▼                ▼
             FAILED        (human rejects → stays READY_FOR_REVIEW
                            or a new attempt is started)
```

- **Nothing publishes itself.** Approval is the only operation that writes
  `Dish.model_url`.
- A failed generation records a safe, human-readable error and never touches
  the dish's existing model.

---

## 6. The Human Process (roles & responsibilities)

| Role | Responsibility | Where |
|---|---|---|
| **Restaurant admin** | Photographs dishes, uploads them, reviews generated models, approves/publishes | Mac browser / admin API |
| **Reviewer (quality gate)** | Decides if a model looks like the real dish before it goes live | `READY_FOR_REVIEW` inspection |
| **Developer** | Runs the Mac backend, keeps tests green, orchestrates Colab runs | Mac + Colab |
| **Colab operator** | Mounts Drive, starts the TRELLIS worker, reports GPU measurements | Colab browser |
| **Guest** | Scans, browses, views 3D/AR | Phone |

**The working rhythm (a single dish):**

1. **Shoot** — take a clean top-down or 3/4 photo of the plated dish.
2. **Upload** — one API call (or future admin UI) stores the photo.
3. **Send to GPU** — the job crosses the Drive bridge; the Colab worker
   picks it up within seconds.
4. **Wait** — TRELLIS reconstructs the dish (minutes on the T4).
5. **Review** — the model returns; a human decides: *does this look like
   chicken biryani?* If yes → approve. If no → it stays for review.
6. **Publish** — the dish now shows a real 3D preview to every guest.
7. **Enjoy** — the guest places the biryani on their table in AR.

---

## 7. Where Things Stand

### Done and verified

| Area | Status |
|---|---|
| Customer QR → menu → dish → 3D/AR flow | Built, working |
| Backend M1–M3 (models, lifecycle, admin API, storage, validation) | Built, 65 tests passing |
| Provider abstraction (`ImageTo3DProvider`) | Built, clean |
| `LocalTrellisProvider` + job protocol | Built, tested (no GPU needed) |
| Colab TRELLIS worker + GPU smoke test | Written, awaiting real T4 run |
| Mac → staging → Drive → Colab → results transport | Built, documented |
| Source-image reachability (cloudflared tunnel) | Verified live (200, image/jpeg) |
| One real end-to-end GPU generation | **In progress** — the single chicken-biryani run |

### Known gaps / honest notes

- **Only 1 of 15 dishes has a model** (`chicken-biryani`). `paneer-tikka` and
  `masala-dosa` reference models that do not exist yet — they fall back to
  photo-only AR until generated.
- **The real GPU proof is not yet complete** — it requires one manual Colab
  run (mount Drive, start worker, sync the staged job, sync results back).
- **`backend/trellis_worker/README.md` is stale** — the authoritative
  operational reference is `backend/docs/TRELLIS_COLAB_DRIVE_TRANSPORT.md`.
- The Drive bridge and tunnel are **development-only** transports; production
  will use real object storage and a persistent worker.

---

## 8. Repo Map (where things live)

```
ARVR/
├── src/                          # Customer frontend (TanStack Start, React 19)
│   ├── routes/                   #   /, /t/$token, dish detail, 3D/AR page
│   ├── components/ar/            #   DishARViewer, CameraArView
│   └── lib/api/                  #   API seam (mock adapter today)
├── public/
│   ├── images/dishes/            #   The 15 dish photos (real photography)
│   └── models/dishes/            #   chicken-biryani.glb/.usdz (only real model)
├── backend/
│   ├── app/
│   │   ├── api/admin.py          #   Admin endpoints
│   │   ├── models/               #   Dish, Generation + lifecycle enum
│   │   ├── services/             #   GenerationService, DishService
│   │   ├── providers/            #   base (ABC), meshy, local_trellis, trellis_jobs
│   │   ├── storage/              #   base (ABC), local
│   │   ├── validation/           #   GLB/USDZ automated checks
│   │   └── workers/              #   background worker factory
│   ├── trellis_worker/           #   Colab-only: run_worker.py, smoke_test.py
│   ├── docs/                     #   GPU architecture + Drive transport guides
│   └── tests/                    #   65 tests, no GPU required
├── scripts/                      #   Asset-pipeline experiments (m17-meshy, etc.)
└── PROJECT_OVERVIEW.md           #   ← this document
```

---

## 9. The Next Steps (the honest path forward)

1. **Complete the one real GPU proof** — run the single chicken-biryani
   generation through the Colab T4 worker and drive it to `READY_FOR_REVIEW`.
2. **Approve it** (human gate) and verify the customer 3D/AR route loads the
   generated model.
3. **Build the admin UI** — a simple page for upload → generate → review →
   approve, so a restaurant can do this without curl.
4. **Generate the missing dishes** (`paneer-tikka`, `masala-dosa`) through
   the proven pipeline.
5. **Replace the dev transport** (Drive + tunnel) with a production storage
   + persistent worker once the architecture is proven.

---

*This document is the living overview of the project: the product, the
people, the process, and the pipeline. When in doubt, the answer to "what
are we doing here?" is: a restaurant photo becomes a guest's 3D dish — for
free, and always reviewed by a human before it goes live.*
