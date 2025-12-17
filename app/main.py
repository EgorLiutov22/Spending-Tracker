from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.database import engine, Base
from app.api import routers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Создает таблицы при запуске, закрывает соединения при остановке.
    """
    # Startup
    logger.info("Starting up Spending Tracker API...")
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Spending Tracker API...")
    await engine.dispose()
    logger.info("Database connections closed")

# Создание FastAPI приложения
app = FastAPI(
    title="Spending Tracker API",
    description="Асинхронное приложение для отслеживания расходов",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене замените на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение всех роутеров
for router in routers:
    app.include_router(router)
    logger.info(f"Router {router.prefix} loaded")

# Корневой эндпоинт
@app.get("/")
async def root():
    return {
        "message": "Welcome to Spending Tracker API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "endpoints": [
            "/auth",
            "/transactions",
            "/categories",
            "/groups",
            "/analytics",
            "/users"
        ]
    }

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "spending-tracker-api",
        "database": "connected"  # Можно добавить проверку подключения к БД
    }

@app.get("/version")
async def version():
    return {
        "version": "2.0.0",
        "async": True,
        "database": "postgresql+asyncpg" if "asyncpg" in str(engine.url) else "sqlite+aiosqlite"
    }