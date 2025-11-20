from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base
from app.auth.auth_handler import get_password_hash, verify_password

class User(Base):
    __tablename__ = "users"

     # Уникальный идентификатор пользователя
    id = Column(Integer, primary_key=True, index=True, comment='Уникальный идентификатор пользователя')  

    # Имя пользователя
    first_name = Column(String(50, nullable=False), comment='Имя пользователя') 

    # Фамилия пользователя
    last_name = Column(String(50, nullable=False),comment='Фамилия пользователя')   

    # Email пользователя
    email = Column(String(100), unique=True, index=True, nullable=False, comment='Email пользователя') 

    # Хешированный пароль
    hashed_password = Column(String(255), nullable=False, comment='Хешированный пароль') 

    # Флаг активности
    is_active = Column(Boolean, default=True, comment='Флаг активности пользователя') 

    # Дата создания
    created_at = Column(DateTime(timezone=True), server_default=func.now(), 
                        comment='Дата и время создания пользователя')
    
    def __repr__(self) -> str:
        """
        Строковое представление пользователя.
        """
        return f"<User(id={self.id}, email='{self.email}')>"
    
    def get_full_name(self) -> str:
        """
        Возвращает полное имя пользователя.
        """
        return f"{self.first_name} {self.last_name}"