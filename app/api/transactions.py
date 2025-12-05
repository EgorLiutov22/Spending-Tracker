from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import enum

from app.database import get_db
from app.services.auth_services import AuthService
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.models.category import Category  # Предполагаем, что есть модель Category

# Схемы Pydantic
from pydantic import BaseModel, ConfigDict, Field




router = APIRouter()


class TransactionTypeEnum(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class TransactionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Transaction name")
    type: TransactionTypeEnum = Field(..., description="Transaction type")
    category_id: int = Field(..., gt=0, description="Category ID")
    amount: float = Field(..., gt=0, description="Transaction amount")
    date: Optional[datetime] = Field(None, description="Transaction date and time")


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[TransactionTypeEnum] = None
    category_id: Optional[int] = Field(None, gt=0)
    amount: Optional[float] = Field(None, gt=0)
    date: Optional[datetime] = None


class CategoryResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    category: CategoryResponse

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    skip: int
    limit: int


# CRUD операции для транзакций
class TransactionCRUD:
    @staticmethod
    def create(db: Session, transaction_in: TransactionCreate, user_id: int):
        # Проверяем существование категории
        category = db.query(Category).filter(Category.id == transaction_in.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )

        # Создаем транзакцию
        db_transaction = Transaction(
            name=transaction_in.name,
            type=TransactionType(transaction_in.type.value),
            category_id=transaction_in.category_id,
            amount=transaction_in.amount,
            date=transaction_in.date or datetime.now(),
            user_id=user_id
        )

        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        return db_transaction

    @staticmethod
    def get_multi_by_user(
            db: Session,
            user_id: int,
            skip: int = 0,
            limit: int = 100,
            category_id: Optional[int] = None,
            type: Optional[TransactionTypeEnum] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ):
        query = db.query(Transaction).filter(Transaction.user_id == user_id)

        # Применяем фильтры
        if category_id:
            query = query.filter(Transaction.category_id == category_id)

        if type:
            query = query.filter(Transaction.type == TransactionType(type.value))

        if start_date:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            query = query.filter(Transaction.date >= start_datetime)

        if end_date:
            end_datetime = datetime.combine(end_date, datetime.max.time())
            query = query.filter(Transaction.date <= end_datetime)

        # Получаем общее количество
        total = query.count()

        # Применяем пагинацию и сортировку
        transactions = query.order_by(Transaction.date.desc(), Transaction.id.desc()) \
            .offset(skip) \
            .limit(limit) \
            .all()

        return transactions, total

    @staticmethod
    def get(db: Session, transaction_id: int, user_id: int):
        return db.query(Transaction) \
            .filter(Transaction.id == transaction_id, Transaction.user_id == user_id) \
            .first()

    @staticmethod
    def update(db: Session, transaction_id: int, transaction_in: TransactionUpdate, user_id: int):
        transaction = TransactionCRUD.get(db, transaction_id, user_id)
        if not transaction:
            return None

        # Проверяем категорию, если она обновляется
        if transaction_in.category_id is not None:
            category = db.query(Category).filter(Category.id == transaction_in.category_id).first()
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category not found"
                )

        # Обновляем поля
        update_data = transaction_in.model_dump(exclude_unset=True)

        # Конвертируем строковый тип в enum, если нужно
        if 'type' in update_data and update_data['type']:
            update_data['type'] = TransactionType(update_data['type'].value)

        for field, value in update_data.items():
            setattr(transaction, field, value)

        db.commit()
        db.refresh(transaction)
        return transaction

    @staticmethod
    def delete(db: Session, transaction_id: int, user_id: int):
        transaction = TransactionCRUD.get(db, transaction_id, user_id)
        if not transaction:
            return False

        db.delete(transaction)
        db.commit()
        return True


# Инициализация CRUD и сервисов
transaction_crud = TransactionCRUD()
auth_service = AuthService()




@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
        transaction_in: TransactionCreate,
        current_user: User = Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Create a new transaction
    - Authenticated users can create transactions
    - Category must exist
    - Amount must be positive
    - Date defaults to current time if not provided
    """
    transaction = transaction_crud.create(
        db=db,
        transaction_in=transaction_in,
        user_id=current_user.id
    )

    return transaction


@router.get("/", response_model=TransactionListResponse)
def get_transactions(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
        category_id: Optional[int] = Query(None, description="Filter by category ID"),
        type: Optional[TransactionTypeEnum] = Query(None, description="Filter by type (income/expense)"),
        start_date: Optional[date] = Query(None, description="Start date for filtering (YYYY-MM-DD)"),
        end_date: Optional[date] = Query(None, description="End date for filtering (YYYY-MM-DD)"),
        current_user: User = Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Get list of transactions with filtering and pagination
    - Returns user's transactions
    - Supports filtering by category, type, and date range
    - Includes pagination for large datasets
    - Results ordered by date (newest first)
    """
    transactions, total = transaction_crud.get_multi_by_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        category_id=category_id,
        type=type,
        start_date=start_date,
        end_date=end_date
    )

    return TransactionListResponse(
        transactions=transactions,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
        transaction_id: int,
        current_user: User = Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Get a single transaction by ID
    - User must own the transaction
    - Returns detailed transaction information with category
    """
    transaction = transaction_crud.get(
        db=db,
        transaction_id=transaction_id,
        user_id=current_user.id
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
        transaction_id: int,
        transaction_in: TransactionUpdate,
        current_user: User = Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Update a transaction
    - Only transaction owner can update
    - Partial updates supported
    - Validates category existence if updating category
    """
    transaction = transaction_crud.update(
        db=db,
        transaction_id=transaction_id,
        transaction_in=transaction_in,
        user_id=current_user.id
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
        transaction_id: int,
        current_user: User = Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Delete a transaction
    - Only transaction owner can delete
    - Permanent deletion
    """
    success = transaction_crud.delete(
        db=db,
        transaction_id=transaction_id,
        user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    return None
