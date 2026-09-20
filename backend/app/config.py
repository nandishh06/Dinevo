"""Application configuration, read from environment variables.

No secrets are hardcoded. A real .env is never committed; see .env.example.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    meshy_api_key: str
    fal_key: str
    image_to_3d_provider: str
    trellis_job_dir: str
    trellis_staging_dir: str
    trellis_results_dir: str
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str


def load_settings() -> Settings:
    return Settings(
        meshy_api_key=os.environ.get("MESHY_API_KEY", ""),
        fal_key=os.environ.get("FAL_KEY", ""),
        image_to_3d_provider=os.environ.get("IMAGE_TO_3D_PROVIDER", "meshy"),
        trellis_job_dir=os.environ.get("TRELLIS_JOB_DIR", "./data/trellis_jobs"),
        trellis_staging_dir=os.environ.get(
            "TRELLIS_STAGING_DIR", "./data/trellis_jobs/staging"
        ),
        trellis_results_dir=os.environ.get(
            "TRELLIS_RESULTS_DIR", "./data/trellis_jobs/results"
        ),
        supabase_url=os.environ.get("SUPABASE_URL", ""),
        supabase_service_role_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        supabase_jwt_secret=os.environ.get("SUPABASE_JWT_SECRET", ""),
    )
