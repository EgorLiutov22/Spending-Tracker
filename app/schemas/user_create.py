from pydantic import BaseModel, EmailStr, field_validator
import re

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        """
        Проверяет, что имя не пустое
        """
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
        Проверяет сложность пароля.
        
        Требования:
        - Минимум 8 символов
        - Минимум 1 заглавная буква
        - Минимум 1 строчная буква  
        - Минимум 1 цифра
        - Минимум 1 специальный символ
        - Не может быть пустым
        - Не может содержать пробелы
        
        Args:
            v: Значение пароля
            
        Returns:
            str: Проверенный пароль
            
        Raises:
            ValueError: Если пароль не соответствует требованиям безопасности
        """
        if not v:
            raise ValueError('Пароль не может быть пустым')
        
        # Убираем пробелы по краям
        password = v.strip()
        
        # Проверка длины
        if len(password) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        
        # Проверка на пробелы внутри пароля
        if ' ' in password:
            raise ValueError('Пароль не может содержать пробелы')
        
        # Проверка заглавных букв
        if not re.search(r'[A-ZА-Я]', password):
            raise ValueError('Пароль должен содержать минимум 1 заглавную букву')
        
        # Проверка строчных букв
        if not re.search(r'[a-zа-я]', password):
            raise ValueError('Пароль должен содержать минимум 1 строчную букву')
        
        # Проверка цифр
        if not re.search(r'\d', password):
            raise ValueError('Пароль должен содержать минимум 1 цифру')
        
        # Проверка специальных символов
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?]', password):
            raise ValueError('Пароль должен содержать минимум 1 специальный символ: !@#$%^&*()_+-=[]{};\':"|,.<>/?')
        
        # Проверка на простые пароли
        weak_passwords = [
            'password', '12345678', 'qwerty', 'admin', 'welcome',
            'пароль', '123456789', '00000000'
        ]
        if password.lower() in weak_passwords:
            raise ValueError('Пароль слишком простой и ненадежный')
        
        # Проверка на последовательности
        if re.search(r'(.)\1{2,}', password):  # 3+ одинаковых символа подряд
            raise ValueError('Пароль не должен содержать 3+ одинаковых символа подряд')
        
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            raise ValueError('Пароль не должен содержать простые числовые последовательности')
        
        return password
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """
        Дополнительная проверка email.
        
        Проверяет что email не из временных доменов.
        """
        temporary_domains = [
            'tempmail.com', '10minutemail.com', 'guerrillamail.com',
            'mailinator.com', 'yopmail.com', 'trashmail.com'
        ]
        
        domain = v.split('@')[-1].lower()
        if domain in temporary_domains:
            raise ValueError('Использование временных email адресов запрещено')
        
        return v