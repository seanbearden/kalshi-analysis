"""API v1 router configuration."""

from fastapi import APIRouter

from .account import router as account_router
from .backtests import router as backtests_router
from .markets import router as markets_router

# Combine all v1 routes
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(markets_router)
api_v1_router.include_router(backtests_router)
api_v1_router.include_router(account_router)

__all__ = ["api_v1_router"]
