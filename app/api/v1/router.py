"""
API v1 router.

All v1 endpoints are registered here. This is the only place where
URL paths are defined for the v1 API.
"""

from fastapi import APIRouter

from app.api.v1.telegram import router as telegram_router
from app.api.v1.users import router as users_router
from app.api.v1.chats import router as chats_router
from app.api.v1.llm import router as llm_router
from app.api.v1.documents import router as documents_router
from app.api.v1.auth import router as auth_router

router = APIRouter(prefix="/api/v1")

# Health check
@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns the application status. Used by Docker, load balancers,
    and monitoring systems to verify the service is running.
    """
    return {
        "status": "ok",
        "service": "AI Personal Assistant",
        "version": "0.4.0",
    }

# Include sub-routers
router.include_router(telegram_router)
router.include_router(users_router)
router.include_router(chats_router)
router.include_router(llm_router)
router.include_router(documents_router)
router.include_router(auth_router)
