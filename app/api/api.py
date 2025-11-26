from fastapi import APIRouter
from . import auth, groups, transactions

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])