"""ImageTo3DProvider — the narrow seam between GenerationService and any
image->3D backend (Meshy today, a self-hosted model later).

GenerationService depends on this protocol, never on MeshyProvider directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderAsset:
    """Resolved downloadable URLs for a completed generation task."""

    glb_url: str
    usdz_url: str | None = None
    preview_urls: dict[str, str] | None = None


@dataclass(frozen=True)
class ProviderTaskStatus:
    """Current state of a provider-side generation task."""

    status: str  # e.g. "PENDING" | "PROCESSING" | "SUCCEEDED" | "FAILED" | "CANCELED"
    progress: int = 0
    error: str | None = None


class ImageTo3DProvider(ABC):
    """Submit an image URL, poll the task, fetch resulting assets.

    The provider receives a STORED/PUBLICLY FETCHABLE image URL — never a
    local file path and never a base64 blob (the backend stores the source
    image first; see AssetStorage).
    """

    name: str

    @abstractmethod
    def submit(self, image_url: str) -> str:
        """Start generation for image_url. Returns the provider task id."""

    @abstractmethod
    def poll(self, task_id: str) -> ProviderTaskStatus:
        """Return the current status of a previously submitted task."""

    @abstractmethod
    def fetch_assets(self, task_id: str) -> ProviderAsset:
        """Fetch downloadable asset URLs for a completed task.

        Called only after poll() reports SUCCEEDED.
        """
