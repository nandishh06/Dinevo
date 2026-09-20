"""Supabase integration for the Dscape SaaS backend.

Kept deliberately small and provider-agnostic at the call sites:

  - :func:`get_supabase` returns a service-role admin client used ONLY on the
    server. It bypasses RLS, so every query built on it MUST be scoped by the
    authenticated owner (enforced in the dashboard service layer).
  - :func:`get_authenticated_user_id` verifies a Supabase Auth JWT (HS256,
    aud="authenticated") and returns the authenticated user's UUID. Client
    supplied user IDs are never trusted.

The service-role key and JWT secret are read from the environment and never
leave the server. Nothing in this module is imported by the frontend.
"""

from __future__ import annotations

import os
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from app.config import Settings, load_settings

_bearer_scheme = HTTPBearer(auto_error=False)


class SupabaseNotConfigured(RuntimeError):
    """Raised when the backend is missing Supabase environment variables."""


@lru_cache(maxsize=1)
def get_supabase(settings: Settings | None = None) -> Client:
    """Return a service-role Supabase admin client (server only).

    Cached so we do not recreate a client per request. Only the URL and
    service-role key are used; the anon key is intentionally never read here.
    """
    s = settings or load_settings()
    if not s.supabase_url or not s.supabase_service_role_key:
        raise SupabaseNotConfigured(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
        )
    return create_client(s.supabase_url, s.supabase_service_role_key)


@lru_cache(maxsize=1)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    """Cached JWKS client for verifying asymmetric (ES256/RS256) tokens."""
    return jwt.PyJWKClient(jwks_url)


def verify_supabase_jwt(token: str, settings: Settings | None = None) -> str:
    """Verify a Supabase Auth access token and return the user UUID (sub).

    Supports both signing modes:
      - ES256/RS256 (current Supabase default): verified against the project's
        JWKS endpoint. No secret is required.
      - HS256 (legacy): verified against SUPABASE_JWT_SECRET.

    Raises jwt.PyJWTError on any invalid/expired token. The audience must be
    "authenticated".
    """
    s = settings or load_settings()

    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "")

    if alg == "HS256":
        if not s.supabase_jwt_secret:
            raise SupabaseNotConfigured("SUPABASE_JWT_SECRET must be set")
        payload = jwt.decode(
            token,
            s.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True, "require": ["sub"]},
        )
    else:
        if not s.supabase_url:
            raise SupabaseNotConfigured("SUPABASE_URL must be set")
        jwks_url = f"{s.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg] if alg else ["ES256", "RS256"],
            audience="authenticated",
            options={"verify_exp": True, "require": ["sub"]},
        )

    sub = payload.get("sub")
    if not sub:
        raise jwt.InvalidTokenError("token missing sub claim")
    return str(sub)


def _extract_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is None or not credentials.scheme.lower() == "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_authenticated_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """FastAPI dependency: verify the bearer token and return the user UUID.

    Any route that depends on this is protected. The returned UUID is the
    server-verified Supabase auth user id — never a value supplied by the
    client as a query/body field.
    """
    token = _extract_bearer_token(credentials)
    try:
        return verify_supabase_jwt(token)
    except SupabaseNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured on the server",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_supabase_settings() -> Settings:
    return load_settings()


def env_has_supabase() -> bool:
    """True when the minimum Supabase config is present (used by tests)."""
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    secret = os.environ.get("SUPABASE_JWT_SECRET", "").strip()
    return bool(url and key and secret)
