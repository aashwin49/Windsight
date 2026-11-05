"""Repository-root entry point for `uvicorn main:app`."""

from backend.app.main import app

__all__ = ["app"]
