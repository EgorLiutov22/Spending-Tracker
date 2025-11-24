from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
