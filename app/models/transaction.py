from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum

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