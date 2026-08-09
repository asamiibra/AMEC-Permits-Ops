"""Zero-configuration Vercel entrypoint for the PermitOps FastAPI app."""

from app.main import app

__all__ = ["app"]
