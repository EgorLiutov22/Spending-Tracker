from .auth import router as auth_router
from .analytics import router as analytics_router
from .categories import router as categories_router
from .groups import router as groups_router
from .transactions import router as transactions_router
from .users import router as users_router


routers = [
    auth_router,
    analytics_router,
    categories_router,
    groups_router,
    transactions_router,
    users_router,
]