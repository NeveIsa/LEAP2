"""FastAPI dependency for admin authentication via session cookie."""

from __future__ import annotations

from fastapi import Request, HTTPException, status


async def require_admin(request: Request) -> None:
    """Dependency that checks for an authenticated admin session."""
    if not request.session.get("admin"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin login required",
        )
