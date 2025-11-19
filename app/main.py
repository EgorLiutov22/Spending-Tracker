from fastapi import FastAPI

from .database import engine, Base
from .models import User, Transaction, Category, Group


app = FastAPI(title="Spending Tracker API")

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