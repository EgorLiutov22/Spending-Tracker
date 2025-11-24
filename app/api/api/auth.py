# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# from app.api.v1.deps import get_db
# from app.services.auth_service import auth_service, get_current_user
# from app.crud.crud_user import user_crud
# from app.schemas.token import Token, RefreshToken
# from app.schemas.user import UserCreate, UserResponse
# from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
        user_in: UserCreate,
        db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = user_crud.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = user_crud.create_with_password(db, obj_in=user_in)
    return user


@router.post("/login", response_model=Token)
def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = auth_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return auth_service.create_tokens(user)


@router.post("/refresh-token", response_model=Token)
def refresh_token(
        token_in: RefreshToken,
        db: Session = Depends(get_db)
):
    """
    Refresh access token
    """
    payload = auth_service.verify_token(token_in.refresh_token)
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

    user = user_crud.get_by_email(db, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return auth_service.create_tokens(user)


@router.post("/change-password")
def change_password(
        current_password: str,
        new_password: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Change user password
    """
    # Verify current password
    if not auth_service.verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    user_crud.update_password(db, user_id=current_user.id, new_password=new_password)

    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return current_user


@router.post("/logout")
def logout():
    """
    Logout user (client should discard tokens)
    """
    return {"message": "Successfully logged out"}