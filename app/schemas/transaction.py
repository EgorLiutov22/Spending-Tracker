from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
from app.models.enums import TransactionType

class TransactionBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: TransactionType
    category_id: int
    amount: float = Field(..., gt=0)
    date: Optional[datetime] = None
    group_id: Optional[int] = None
    
    @validator('amount')
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[TransactionType] = None
    category_id: Optional[int] = None
    amount: Optional[float] = Field(None, gt=0)
    date: Optional[datetime] = None
    group_id: Optional[int] = None

class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    category_name: Optional[str] = None
    group_name: Optional[str] = None
    
    class Config:
        from_attributes = True