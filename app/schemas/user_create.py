from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Имя не может быть пустым')
        return v.strip()
    
    @field_validator('last_name')
    @classmethod
    def validate_last_name(cls, v:str) -> str:
        if not v or not v.strip():
            raise ValueError('Фамилия не может быть пустой')
        return v.strip()       
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Требования:
        - Минимум 5 символов
        - Не может быть пустым
        """
        if not v:
            raise ValueError('Пароль не может быть пустым')
        if len(v) < 5:
            raise ValueError('Пароль должен содержать минимум 5 символов')
        return v