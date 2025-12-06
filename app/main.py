from fastapi import FastAPI

from .database import engine, Base
from .api.transactions import transaction_router as transactions_router
from .routers import api_router

app = FastAPI(title="Spending Tracker API")
app.include_router(api_router)

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
