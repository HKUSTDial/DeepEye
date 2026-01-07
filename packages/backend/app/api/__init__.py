"""API package."""

# Avoid eager imports that can trigger circular imports during app startup.
__all__ = ["auth", "public", "v1"]
