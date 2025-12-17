from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user_response_schema import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = Depends(get_current_user)
):
    """
    Получить информацию о текущем пользователе
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Преобразуем модель User в схему UserResponse
    # В схеме ожидается id, а не uid
    return UserResponse(
        id=current_user.id,  # Используем id вместо uid
        email=current_user.email,
        status=current_user.is_active,  # status в схеме соответствует is_active в модели
        first_name=current_user.first_name,
        last_name=current_user.last_name
    )