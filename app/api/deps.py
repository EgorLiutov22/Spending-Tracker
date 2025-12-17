from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth_service import auth_service


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(auth_service.security)
) -> AsyncGenerator:
    """
    Асинхронная зависимость для получения текущего пользователя.
    Используется в роутерах для защиты эндпоинтов.
    """
    try:
        user = await auth_service.get_current_user(token, db)
        yield user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронная зависимость для получения сессии БД.
    Альтернатива get_db для явного использования.
    """
    async for session in get_db():
        yield session