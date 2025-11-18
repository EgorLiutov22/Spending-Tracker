from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class TransactionType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Transaction(Base):
    
    __tablename__ = "transactions"
    
    # Уникальный идентификатор транзакции
    id = Column(Integer, primary_key=True, index=True, comment="Уникальный идентификатор транзакции")
    
    # Название/описание транзакции
    name = Column(String(100), nullable=False,
                   comment="Название или описание транзакции. Например: 'Зарплата', 'Продукты'")
    
    # Тип транзакции (доход/расход)
    type = Column(SQLEnum(TransactionType), nullable=False, 
                  comment="Тип транзакции: income (доход) или expense (расход)")
    
    # Категория транзакции
    category = Column(String(50), nullable=False,
        comment="Категория транзакции. Например: 'Еда', 'Транспорт', 'Зарплата'")
    
    # Сумма транзакции (всегда положительная)
    amount = Column(Float, nullable=False,
        comment="Сумма транзакции. Всегда положительное число")
    
    # Дата и время транзакции
    date = Column(DateTime(timezone=True), server_default=func.now(),
        comment="Дата и время совершения транзакции. По умолчанию текущее время")
    
    # Связь с пользователем
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False,
        comment="ID пользователя, которому принадлежит транзакция")
    
    # Отношение с пользователем
    user = relationship("User", back_populates="transactions")
    