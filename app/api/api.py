from fastapi import APIRouter
from . import auth, groups, transactions

api_router = APIRouter()

api_router.include_router(auth.auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(groups.group_router, prefix="/groups", tags=["groups"])
api_router.include_router(transactions.transaction_router, prefix="/transactions", tags=["transactions"])