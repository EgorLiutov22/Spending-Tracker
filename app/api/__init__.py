from .auth import auth_router as auth_router
from .groups import group_router as groups_router
from .transactions import transaction_router as transactions_router

__all__ = ["auth_router", "groups_router", "transactions_router"]
from .analytics import analytic_router as analytics_router
from .categories import category_router as categories_router
from .groups import group_router as groups_router
from .transactions import transaction_router as transactions_router
from .users import router as users_router


routers = [
    auth_router,
    analytics_router,
    categories_router,
    groups_router,
    transactions_router,
    users_router,
]
