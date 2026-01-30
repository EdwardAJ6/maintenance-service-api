"""Routers module."""

from .categories import router as categories_router
from .items import router as items_router
from .orders import router as orders_router
from .auth import router as auth_router

__all__ = ["categories_router", "items_router", "orders_router", "auth_router"]
