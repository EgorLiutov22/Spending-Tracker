from pydantic import BaseModel, EmailStr


class UserLogin(BaseModel):
    login: str  # Может быть email или username
    password: str


class Cfig:
    schema_extra = {
        "example": {
            "login": "user@example.com","password": "SecurePass123!"
        }
    }