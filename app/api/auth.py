from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.services.auth_service import auth_service
from app.schemas.token_schema import Token
from app.schemas.user_response_schema import UserResponse
from app.schemas.user_create_schema import UserCreate
from app.models.user import User

auth_router = APIRouter(prefix="/auth", tags=["authentication"])

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрация нового пользователя.
    Требует email, пароль, имя и фамилию.
    """
    # Проверяем, существует ли пользователь с таким email
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Хэшируем пароль
    hashed_password = auth_service.pwd_context.hash(user_in.password)
    
    # Создаем пользователя
    user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        email=user_in.email,
        hashed_password=hashed_password,
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user

@auth_router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Аутентификация пользователя.
    Возвращает JWT токен для доступа к защищенным эндпоинтам.
    """
    # Ищем пользователя по email
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not auth_service.pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Создаем access токен
    access_token = auth_service.create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@auth_router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Получение информации о текущем пользователе.
    Требует JWT токен в заголовках.
    """
    return current_user

@auth_router.post("/logout")
async def logout():
    """
    Выход из системы.
    Клиент должен удалить токен на своей стороне.
    """
    return {"message": "Successfully logged out"}

@auth_router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Смена пароля текущего пользователя.
    """
    # Проверяем текущий пароль
    if not auth_service.pwd_context.verify(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Обновляем пароль
    current_user.hashed_password = auth_service.pwd_context.hash(new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}