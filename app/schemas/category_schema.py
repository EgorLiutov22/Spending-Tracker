# app/schemas/category_schema.py

from pydantic import BaseModel
from typing import Optional

class CategoryBase(BaseModel):
    name: str
    type: str  # "income" or "expense"
    group_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    group_id: Optional[int] = None

class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True  # для SQLAlchemy >= 2.0 (ранее было orm_mode = True)
