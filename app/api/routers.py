# app/api/routers.py
from fastapi import APIRouter
from .auth import auth_router
from .analytics import router as analytics_router
from .categories import category_router
from .groups import group_router
from .transactions import transaction_router
from .users import router as users_router

# Создаем основной роутер
api_router = APIRouter()

# Подключаем все роутеры
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(category_router, prefix="/categories", tags=["categories"])
api_router.include_router(group_router, prefix="/groups", tags=["groups"])
api_router.include_router(transaction_router, prefix="/transactions", tags=["transactions"])
api_router.include_router(users_router, prefix="/users", tags=["users"])

__all__ = ["api_router"]