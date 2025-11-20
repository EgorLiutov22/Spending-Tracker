from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user_create import UserCreate
from app.auth.get_user_by_email import get_user_by_email


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Создает нового пользователя с хешированным паролем.
    """
    # Проверяем что email свободен
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    # Создаем пользователя
    db_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
    )
    
    # Хешируем пароль
    db_user.set_password(user_data.password)
    
    # Сохраняем в БД
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user