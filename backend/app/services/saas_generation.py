"""SaasGenerationService — Supabase-backed image->3D lifecycle for SaaS menu items.

Operates on Supabase `menu_items` + `generations` (NOT the legacy SQLite
Dish/Generation). The existing provider seam (ImageTo3DProvider) and GLB
validation are reused unchanged.

Owner-scoped methods take a server-verified user id and enforce tenant
ownership. The worker method (`run_generation`) is called in the background
with a service-role client and no user context.
"""

from __future__ import annotations

import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError

from fastapi import HTTPException, status
from supabase import Client

from app.providers.base import ImageTo3DProvider, ProviderTaskStatus
from app.validation.glb import validate_generated_assets

MODELS_BUCKET = "restaurant-models"

# generation.status values (also enforced by a DB check constraint).
GENERATION_QUEUED = "QUEUED"
GENERATION_PROCESSING = "PROCESSING"
GENERATION_COMPLETED = "COMPLETED"
GENERATION_FAILED = "FAILED"

# menu_items.model_status values.
MODEL_GENERATING = "GENERATING"
MODEL_READY = "READY"
MODEL_FAILED = "FAILED"

_ACTIVE_STATUSES = (GENERATION_QUEUED, GENERATION_PROCESSING)
_TERMINAL_PROVIDER = ("SUCCEEDED", "FAILED", "CANCELED")


class DuplicateGenerationError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A generation is already in progress for this dish",
        )


class SaasGenerationService:
    def __init__(self, supabase: Client, provider: ImageTo3DProvider | None = None) -> None:
        self._db = supabase
        self._provider = provider

    # -- owner-scoped ------------------------------------------------------

    def create_generation(
        self, user_id: str, menu_item_id: str, provider_name: str = "fal"
    ) -> dict:
        """Create a QUEUED generation for a dish (returns immediately).

        Verifies ownership, verifies an image exists, prevents duplicate active
        generations, sets menu_items.model_status = GENERATING.
        """
        item = self._require_menu_item(user_id, menu_item_id)
        if not item.get("image_url"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dish has no image; upload one first",
            )
        if self._has_active_generation(menu_item_id):
            raise DuplicateGenerationError()

        gen = (
            self._db.table("generations")
            .insert(
                {"menu_item_id": menu_item_id, "provider": provider_name, "status": GENERATION_QUEUED}
            )
            .execute()
        )
        if not gen.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create generation",
            )
        generation = gen.data[0]

        self._db.table("menu_items").update(
            {"model_status": MODEL_GENERATING, "model_url": None}
        ).eq("id", menu_item_id).execute()

        return generation

    def get_generation(self, user_id: str, menu_item_id: str) -> dict | None:
        """Return the latest generation for a dish (owner-scoped)."""
        self._require_menu_item(user_id, menu_item_id)
        rows = (
            self._db.table("generations")
            .select("*")
            .eq("menu_item_id", menu_item_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return rows.data[0] if rows.data else None

    # -- worker ------------------------------------------------------------

    def run_generation(self, generation_id: str) -> dict:
        """Execute one generation end-to-end (background worker).

        Requires a wired provider. Downloads -> validates -> stores the GLB in
        Supabase Storage, then publishes model_url / model_status = READY.
        """
        if self._provider is None:
            raise RuntimeError("SaasGenerationService has no provider wired")

        generation = self._get_generation(generation_id)
        if generation["status"] not in _ACTIVE_STATUSES:
            return generation

        item = self._get_menu_item(generation["menu_item_id"])
        image_url = item.get("image_url")
        if not image_url:
            return self.fail_generation(generation_id, "dish has no source image")

        self._db.table("generations").update(
            {"status": GENERATION_PROCESSING, "error": None}
        ).eq("id", generation_id).execute()

        try:
            task_id = self._provider.submit(image_url)
            self._db.table("generations").update(
                {"provider_task_id": task_id}
            ).eq("id", generation_id).execute()

            task = self._poll_until_terminal(task_id)
            if task.status != "SUCCEEDED":
                return self.fail_generation(generation_id, task.error or task.status)

            assets = self._provider.fetch_assets(task_id)
            glb_url = self._download_validate_store(
                generation_id,
                item,
                assets.glb_url,
            )

            self._db.table("generations").update(
                {"status": GENERATION_COMPLETED, "glb_url": glb_url}
            ).eq("id", generation_id).execute()
            self._db.table("menu_items").update(
                {"model_url": glb_url, "model_status": MODEL_READY}
            ).eq("id", generation["menu_item_id"]).execute()
            return self._get_generation(generation_id)
        except Exception as exc:  # noqa: BLE001 - surface provider failures
            return self.fail_generation(generation_id, _safe_error(exc))

    def fail_generation(self, generation_id: str, error: str) -> dict:
        """Mark a generation FAILED and the dish model_status = FAILED."""
        self._db.table("generations").update(
            {"status": GENERATION_FAILED, "error": error[:500]}
        ).eq("id", generation_id).execute()
        generation = self._get_generation(generation_id)
        self._db.table("menu_items").update(
            {"model_status": MODEL_FAILED}
        ).eq("id", generation["menu_item_id"]).execute()
        return generation

    # -- helpers -----------------------------------------------------------

    def _has_active_generation(self, menu_item_id: str) -> bool:
        rows = (
            self._db.table("generations")
            .select("id")
            .eq("menu_item_id", menu_item_id)
            .in_("status", list(_ACTIVE_STATUSES))
            .limit(1)
            .execute()
        )
        return bool(rows.data)

    def _require_menu_item(self, user_id: str, menu_item_id: str) -> dict:
        rows = (
            self._db.table("menu_items")
            .select("*, restaurants!inner(owner_id)")
            .eq("id", menu_item_id)
            .execute()
        )
        for row in rows.data or []:
            if row.get("restaurants") and row["restaurants"].get("owner_id") == user_id:
                return row
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found"
        )

    def _get_generation(self, generation_id: str) -> dict:
        rows = (
            self._db.table("generations")
            .select("*")
            .eq("id", generation_id)
            .execute()
        )
        if not rows.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found"
            )
        return rows.data[0]

    def _get_menu_item(self, menu_item_id: str) -> dict:
        rows = (
            self._db.table("menu_items")
            .select("*")
            .eq("id", menu_item_id)
            .execute()
        )
        if not rows.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found"
            )
        return rows.data[0]

    def _poll_until_terminal(self, task_id: str) -> ProviderTaskStatus:
        deadline = time.monotonic() + 900.0  # 15 min cap for fal.ai TRELLIS
        while True:
            task = self._provider.poll(task_id)
            if task.status in _TERMINAL_PROVIDER:
                return task
            if time.monotonic() >= deadline:
                return ProviderTaskStatus(status="FAILED", error="generation timed out")
            time.sleep(10.0)

    def _download_validate_store(
        self, generation_id: str, item: dict, source_url: str
    ) -> str:
        """Download the provider GLB, validate it, store in Supabase Storage."""
        with tempfile.TemporaryDirectory() as tmp:
            glb_path = Path(tmp) / "model.glb"
            _download(source_url, glb_path)
            result = validate_generated_assets(glb_path, None)
            if not result.ok:
                raise RuntimeError("validation failed: " + "; ".join(result.errors))

            restaurant_id = item["restaurant_id"]
            menu_item_id = item["id"]
            storage_key = (
                f"restaurants/{restaurant_id}/menu/{menu_item_id}/models/{generation_id}.glb"
            )
            data = glb_path.read_bytes()
            self._db.storage.from_(MODELS_BUCKET).upload(
                storage_key, data, {"content-type": "model/gltf-binary"}
            )
            return self._db.storage.from_(MODELS_BUCKET).get_public_url(storage_key)


def _download(url: str, dest: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=300) as resp:  # noqa: S310
            with dest.open("wb") as out:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"download failed for {url}: {exc}") from exc


def _safe_error(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    return text[:500]
