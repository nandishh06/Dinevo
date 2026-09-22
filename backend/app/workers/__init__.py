"""Background generation worker for the Supabase-backed SaaS flow.

Runs SaasGenerationService.run_generation() for a generation id via FastAPI
BackgroundTasks (or directly in tests). No Celery/Redis/queue.
"""

from __future__ import annotations

import logging

from app.config import Settings, load_settings
from app.providers.base import ImageTo3DProvider

logger = logging.getLogger("dscape.backend")


def build_provider(settings: Settings) -> ImageTo3DProvider:
    """Select the image->3D provider from IMAGE_TO_3D_PROVIDER.

      "fal"     -> FalTrellisProvider (fal.ai TRELLIS; requires FAL_KEY)
      "trellis" -> LocalTrellisProvider (free/local GPU job protocol)
    """
    provider_name = settings.image_to_3d_provider

    if provider_name == "trellis":
        from app.providers.local_trellis import LocalTrellisProvider

        return LocalTrellisProvider(job_root=settings.trellis_job_dir)
    if provider_name == "fal":
        from app.providers.fal_trellis import FalTrellisProvider

        return FalTrellisProvider(api_key=settings.fal_key)
    raise RuntimeError(
        f"Unsupported IMAGE_TO_3D_PROVIDER: {provider_name!r} "
        "(supported: 'fal', 'trellis')"
    )


def run_saas_generation_in_background(generation_id: str) -> None:
    """Execute one SaaS generation (Supabase) end-to-end.

    Uses a service-role Supabase client (no user context) and the selected
    provider. Runs on FastAPI's BackgroundTasks thread pool.
    """
    settings = load_settings()
    try:
        provider = build_provider(settings)
    except RuntimeError as exc:
        _fail_saas_generation(settings, generation_id, str(exc))
        return

    from app.services.saas_generation import SaasGenerationService
    from app.supabase import get_supabase

    try:
        supabase = get_supabase(settings)
    except Exception as exc:  # noqa: BLE001
        _fail_saas_generation(settings, generation_id, str(exc))
        return

    service = SaasGenerationService(supabase, provider)
    service.run_generation(generation_id)


def _fail_saas_generation(settings: Settings, generation_id: str, error: str) -> None:
    try:
        from app.services.saas_generation import SaasGenerationService
        from app.supabase import get_supabase

        supabase = get_supabase(settings)
        SaasGenerationService(supabase).fail_generation(generation_id, error)
    except Exception as exc:  # noqa: BLE001
        logger.error("failed to record SaaS generation failure %s: %s", generation_id, exc)
