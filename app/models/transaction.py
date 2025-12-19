from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum
from typing import Dict, Any

from app.database import Base
from app.models.enums import TransactionType


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete='CASCADE'), nullable=False)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete='CASCADE'), nullable=True)
    
    __table_args__ = (
        CheckConstraint('amount >= 0', name='check_amount_positive'),
    )
    
    # Отношения
    category = relationship("Category", back_populates="transactions")
    user = relationship("User", back_populates="transactions")
    group = relationship("Group", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, name='{self.name}', amount={self.amount}, type='{self.type.value}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект транзакции в словарь для экспорта.
        
        Returns:
            Словарь с данными транзакции
        """
        result = {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'amount': float(self.amount) if self.amount else 0.0,
            'date': self.date.isoformat() if self.date else None,
            'category_id': self.category_id,
            'user_id': self.user_id,
            'group_id': self.group_id,
        }
        
        # Добавляем связанные данные, если они загружены
        try:
            if self.category and hasattr(self.category, 'name'):
                result['category_name'] = self.category.name
            else:
                result['category_name'] = None
        except Exception:
            result['category_name'] = None
            
        try:
            if self.group and hasattr(self.group, 'name'):
                result['group_name'] = self.group.name
            else:
                result['group_name'] = None
        except Exception:
            result['group_name'] = None
            
        try:
            if self.user and hasattr(self.user, 'email'):
                result['user_email'] = self.user.email
            else:
                result['user_email'] = None
        except Exception:
            result['user_email'] = None
            
        return result