"""
Top-level shim for platforms that expect `app:app`.

This file re-exports the FastAPI ASGI application defined in
`backend.app.main:app` so callers like `gunicorn app:app` work
without changing the project layout.
"""
from backend.app.main import app  # noqa: F401
