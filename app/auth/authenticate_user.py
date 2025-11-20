from sqlalchemy.orm import Session
from typing import Optional

from app.models.user import User
from app.auth.get_user_by_email import get_user_by_email


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Аутентифицирует пользователя по email и паролю.
    """
    # Ищем пользователя по email
    user = get_user_by_email(db, email)
    if not user:
        return None
    
    # Проверяем пароль
    if not user.check_password(password):
        return None
    
    # Проверяем что пользователь активен
    if not user.is_active:
        return None
    
    return user