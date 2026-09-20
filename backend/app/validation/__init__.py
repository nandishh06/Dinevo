"""Automated asset validation.

Automated checks are a FOUNDATION here: they gate promotion to
READY_FOR_REVIEW, but they never publish an asset and never replace the
human visual quality gate (which happens at APPROVED in a later milestone).

This milestone implements existence/size checks plus a minimal GLB container
check. Deeper checks (glTF parse, bounds, USDZ inspection) land with the M2
worker that actually downloads real assets.
"""
