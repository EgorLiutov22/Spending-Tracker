from pydantic import BaseModel, EmailStr, field_validator

import re

class UserLogin(BaseModel):
    login: str  # Может быть email или username
    password: str

    @field_validator('login')
    def validate_login(cls, v):
        if not v:
            raise ValueError('Логин не может быть пустым')

        v = v.strip()

        if len(v) < 3:
            raise ValueError('Логин должен содержать минимум 3 символа')
        if len(v) > 255:
            raise ValueError('Логин слишком длинный')

        # Проверка на пробелы
        if ' ' in v:
            raise ValueError('Логин не должен содержать пробелы')

        # Проверка, является ли логин email-ом
        if '@' in v:
            # Валидация email с помощью регулярного выражения
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Некорректный формат email. Должен содержать @ и домен')

        return v

    @field_validator('password')
    def validate_password(cls, v):
        if not v:
            raise ValueError('Пароль не может быть пустым')
        if len(v) < 6:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        if len(v) > 128:
            raise ValueError('Пароль слишком длинный')

        # Проверка сложности пароля (опционально)
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isalpha() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну букву')

        return v


class Config:
    schema_extra = {
        "example": {
            "login": "user@example.com","password": "SecurePass123!"
        }
    }