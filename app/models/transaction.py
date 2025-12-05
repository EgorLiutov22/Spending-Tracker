from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class TransactionType(enum.Enum):
    INCOME = "income"   # доход
    EXPENSE = "expense"    # расход


class Transaction(Base):
   
    __tablename__ = "transactions"
    
    # Уникальный идентификатор транзакции
    id = Column(
        Integer, 
        primary_key=True, 
        index=True,
        comment="Уникальный идентификатор транзакции. Первичный ключ таблицы."
    )
    
    # Название/описание транзакции
    name = Column(
        String(100), 
        nullable=False,
        comment="Название или описание транзакции. Например: 'Зарплата', 'Продукты'"
    )
    
    # Тип транзакции (доход/расход)
    type = Column(
        SQLEnum(TransactionType), 
        nullable=False,
        comment="Тип транзакции: income (доход) или expense (расход)"
    )
    
    # Связь с категорией 
    category_id = Column(
        Integer, 
        ForeignKey("categories.id", ondelete='CASCADE'),  # предполагаем что таблица называется categories
        nullable=False,
        comment="ID категории транзакции. Внешний ключ к таблице categories."
    )
    
    # Сумма транзакции
    amount = Column(
        Numeric(precision=10, scale=2), 
        nullable=False,
        comment="Сумма транзакции. Всегда положительное число"
    )
    
    # Дата и время транзакции
    date = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Дата и время совершения транзакции. По умолчанию текущее время"
    )
    
    # Связь с пользователем
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete='CASCADE'), 
        nullable=False,
        comment="ID пользователя, которому принадлежит транзакция"
    )

  # Связь с группой 
    group_id = Column(
        Integer, 
        ForeignKey("groups.id", ondelete='CASCADE'),  # ondelete='CASCADE' или 'SET NULL'
        nullable=True,  # Транзакция может не принадлежать ни к какой группе
        comment="ID группы, к которой относится транзакция. Может быть NULL."
    )

    # Отношение с категорией 
    category = relationship("Category", back_populates="transactions")
    
    # Отношение с пользователем
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self) -> str:
        """
        Строковое представление транзакции.
        """
        return f"<Transaction(id={self.id}, name='{self.name}', amount={self.amount}, type='{self.type.value}, group_id={self.group_id})>"
    
    def to_dict(self) -> dict:
        """
        Преобразует транзакцию в словарь.
        """
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,  # включаем имя категории
            'amount': float(self.amount) if self.amount else None,
            'date': self.date.isoformat() if self.date else None,
            'user_id': self.user_id,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None  # Добавляем имя группы
        }