from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    # Уникальный идентификатор пользователя
    id = Column(Integer, primary_key=True, index=True)

    # Имя пользователя
    first_name = Column(String(50), nullable=False)

    # Фамилия пользователя
    last_name = Column(String(50), nullable=False)

    # Email пользователя
    email = Column(String(100), unique=True, index=True, nullable=False)

    # Хешированный пароль
    hashed_password = Column(String(255), nullable=False)

    # Флаг активности
    is_active = Column(Boolean, default=True)

    # Дата создания
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Отношения (важно использовать lazy="selectin" для асинхронной работы)
    transactions = relationship(
        "Transaction", 
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    categories = relationship(
        "Category", 
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    groups = relationship(
        "Group",
        secondary="user_group_association",
        back_populates="members",
        lazy="selectin"  # Ключевое изменение для асинхронной работы
    )
    
    owned_groups = relationship(
        "Group",
        back_populates="owner",
        foreign_keys="Group.owner_id",
        lazy="selectin"  # Ключевое изменение для асинхронной работы
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self) -> dict:
        """Конвертация объекта пользователя в словарь"""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "full_name": self.get_full_name()
        }
    
    def to_response_dict(self) -> dict:
        """Версия для ответа API (без чувствительных данных)"""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "full_name": self.get_full_name(),
            "groups_count": len(self.groups) if hasattr(self, 'groups') else 0,
            "owned_groups_count": len(self.owned_groups) if hasattr(self, 'owned_groups') else 0
        }