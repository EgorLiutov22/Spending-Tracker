# app/api/users.py

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

# Можно добавить временный эндпоинт для проверки
@router.get("/me")
def read_current_user():
    return {"user_id": 1, "username": "test_user"}