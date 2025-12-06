from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.category_schema import CategoryBase, CategoryCreate, CategoryUpdate
from app.services.category_service import CategoryService


category_router = APIRouter(prefix="/categories", tags=["categories"])


@category_router.post("/", response_model=CategoryBase, status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db)
):
    try:
        return CategoryService.create_category(db, category)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@category_router.get("/", response_model=List[CategoryBase])
def get_categories(
    db: Session = Depends(get_db)
):
    return CategoryService.get_categories(db)


@category_router.get("/{category_id}", response_model=CategoryBase)
def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    db_category = CategoryService.get_category_by_id(db, category_id)
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return db_category


@category_router.put("/{category_id}", response_model=CategoryBase)
def update_category(
    category_id: int,
    category: CategoryUpdate,
    db: Session = Depends(get_db)
):
    try:
        db_category = CategoryService.update_category(db, category_id, category)
        if db_category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        return db_category
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@category_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    deleted = CategoryService.delete_category(db, category_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return None
