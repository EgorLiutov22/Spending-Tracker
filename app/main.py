from fastapi import FastAPI

from .database import engine, Base
from .api.transactions import router as transactions_router
from .api.categories import router as categories_router
from .api.groups import router as groups_router
from .api.auth import router as auth_router
from .api.analytics import router as analytics_router

app = FastAPI(title="Spending Tracker API")
app.include_router(transactions_router)
app.include_router(transactions_router)
app.include_router(categories_router)
app.include_router(groups_router)
app.include_router(auth_router)
app.include_router(analytics_router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()


@app.get("/")
def root():
    return {"message": "Hello"}
