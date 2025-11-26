from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.category import Category as CategoryModel
from app.schemas.category_schema import CategoryCreate, CategoryUpdate


class CategoryService:
    @staticmethod
    def create_category(db: Session, category: CategoryCreate) -> CategoryModel:
        existing_category = db.query(CategoryModel).filter(CategoryModel.name == category.name).first()
        if existing_category:
            raise ValueError(f"Category with name '{category.name}' already exists")

        db_category = CategoryModel(
            name=category.name,
            description=category.description
        )
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category

    @staticmethod
    def get_categories(db: Session) -> List[CategoryModel]:
        return db.query(CategoryModel).all()

    @staticmethod
    def get_category_by_id(db: Session, category_id: int) -> Optional[CategoryModel]:
        return db.query(CategoryModel).filter(CategoryModel.id == category_id).first()

    @staticmethod
    def update_category(db: Session, category_id: int, category: CategoryUpdate) -> Optional[CategoryModel]:
        db_category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
        if not db_category:
            return None

        if category.name and category.name != db_category.name:
            existing_category = db.query(CategoryModel).filter(
                CategoryModel.name == category.name,
                CategoryModel.id != category_id
            ).first()
            if existing_category:
                raise ValueError(f"Category with name '{category.name}' already exists")

        update_data = category.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_category, field, value)

        db.commit()
        db.refresh(db_category)
        return db_category

    @staticmethod
    def delete_category(db: Session, category_id: int) -> bool:
        db_category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
        if not db_category:
            return False

        db.delete(db_category)
        db.commit()
        return True
