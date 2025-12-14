from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import auth_service
from app.schemas.token_schema import Token
from app.schemas.user_response_schema import UserResponse
from app.schemas.user_create_schema import UserCreate
from app.models.user import User


auth_router = APIRouter()


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
        user_in: UserCreate,
        db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    from app.services.auth_service import auth_service

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
    db.commit()
    db.refresh(user)

    return user


@auth_router.post("/login", response_model=Token)
def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Аутентификация пользователя
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not auth_service.pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Создаем токены
    access_token = auth_service.create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@auth_router.post("/refresh-token", response_model=Token)
def refresh_token(
        refresh_token: str,
        db: Session = Depends(get_db)
):
    """
    Refresh access token
    """
    payload = auth_service.verify_token(refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    email: str = payload.get("sub")
    token_type: str = payload.get("type")

    if email is None or token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Создаем новый access token
    access_token = auth_service.create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@auth_router.post("/change-password")
def change_password(
        current_password: str,
        new_password: str,
        current_user: User = Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Change user password
    """
    # Verify current password
    if not auth_service.pwd_context.verify(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    current_user.hashed_password = auth_service.pwd_context.hash(new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@auth_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(auth_service.get_current_user)):
    """
    Get current user information
    """
    return current_user


@auth_router.post("/logout")
def logout():
    """
    Logout user (client should discard tokens)
    """
    return {"message": "Successfully logged out"}