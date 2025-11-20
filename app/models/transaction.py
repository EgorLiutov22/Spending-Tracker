from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class TransactionType(enum.Enum):
    """
    Типы финансовых транзакций.
    
    Values:
        INCOME: Доход (деньги поступают)
        EXPENSE: Расход (деньги уходят)
    """
    INCOME = "income"
    EXPENSE = "expense"


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
        ForeignKey("categories.id"),  # предполагаем что таблица называется categories
        nullable=False,
        comment="ID категории транзакции. Внешний ключ к таблице categories."
    )
    
    # Сумма транзакции
    amount = Column(
        Float, 
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
        ForeignKey("users.id"), 
        nullable=False,
        comment="ID пользователя, которому принадлежит транзакция"
    )
    
    # Отношение с категорией 
    category = relationship("Category", back_populates="transactions")
    
    # Отношение с пользователем
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self) -> str:
        """
        Строковое представление транзакции.
        """
        return f"<Transaction(id={self.id}, name='{self.name}', amount={self.amount}, type='{self.type.value}')>"
    
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
            'amount': self.amount,
            'date': self.date.isoformat() if self.date else None,
            'user_id': self.user_id
        }