from .auth import auth_router
from .analytics import router as analytics_router
from .categories import category_router
from .groups import router as group_router
from .transactions import transaction_router
from .users import router as users_router

__all__ = [
    "auth_router",
    "analytics_router",
    "category_router",
    "group_router",
    "transaction_router",
    "users_router",
]

# Список роутеров (для обратной совместимости)
routers = [
    auth_router,
    analytics_router,
    category_router,
    group_router,
    transaction_router,
    users_router,
]