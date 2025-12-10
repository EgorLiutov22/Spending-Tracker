from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import logging

from app.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.models.enums import TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse
)
from app.services.transaction import TransactionService

# Настройка логирования
logger = logging.getLogger(__name__)

transaction_router = APIRouter()

# Инициализация сервисов
auth_service = AuthService()


@transaction_router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
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
    - Optional group_id for group transactions
    """
    try:
        # Создание сервиса для работы с транзакциями
        transaction_service = TransactionService(db)
        
        # Создание транзакции с использованием сервисного слоя
        transaction = transaction_service.create_transaction(transaction_in, current_user.id)
        return transaction
    except ValueError as e:
        # Валидационная ошибка (например, несуществующая категория)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Логируем внутреннюю ошибку для отладки
        logger.error(f"Error creating transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@transaction_router.get("/", response_model=TransactionListResponse)
def get_transactions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    type: Optional[TransactionType] = Query(None, description="Filter by type (income/expense)"),
    start_date: Optional[date] = Query(None, description="Start date for filtering (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for filtering (YYYY-MM-DD)"),
    group_id: Optional[int] = Query(None, description="Filter by group ID"),
    sort_by: str = Query("date", description="Sort field (date, amount, name)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of transactions with filtering and pagination
    - Returns user's transactions
    - Supports filtering by category, type, date range, and group
    - Includes pagination for large datasets
    - Results ordered by date (newest first) by default
    """
    try:
        # Инициализация сервиса транзакций
        transaction_service = TransactionService(db)
        
        # Преобразование date в datetime для корректной фильтрации
        start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None
        
        # Получение транзакций с применением фильтров и пагинации
        transactions, total = transaction_service.get_user_transactions(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            category_id=category_id,
            start_date=start_datetime,
            end_date=end_datetime,
            type=type,
            group_id=group_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return TransactionListResponse(
            transactions=transactions,
            total=total,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        # Логирование ошибки при получении транзакций
        logger.error(f"Error getting transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@transaction_router.get("/{transaction_id}", response_model=TransactionResponse)
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
    # Получение конкретной транзакции по ID
    transaction_service = TransactionService(db)
    transaction = transaction_service.get_transaction(transaction_id, current_user.id)
    
    # Проверка существования транзакции и прав доступа
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction


@transaction_router.put("/{transaction_id}", response_model=TransactionResponse)
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
    - Validates group existence if updating group
    """
    try:
        transaction_service = TransactionService(db)
        
        # Обновление транзакции через сервисный слой
        transaction = transaction_service.update_transaction(
            transaction_id=transaction_id,
            user_id=current_user.id,
            update_data=transaction_in
        )
        
        # Проверка, найдена ли транзакция
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )
        
        return transaction
    except ValueError as e:
        # Ошибка валидации (например, несуществующая категория)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Логирование внутренней ошибки
        logger.error(f"Error updating transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@transaction_router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
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
    # Удаление транзакции через сервисный слой
    transaction_service = TransactionService(db)
    success = transaction_service.delete_transaction(transaction_id, current_user.id)
    
    # Проверка успешности удаления
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Возвращаем пустой ответ со статусом 204
    return None


@transaction_router.get("/analytics/summary")
def get_financial_summary(
    start_date: Optional[date] = Query(None, description="Start date for summary"),
    end_date: Optional[date] = Query(None, description="End date for summary"),
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get financial summary (income, expense, balance)
    - Can be filtered by date range
    - Returns aggregated data
    """
    try:
        transaction_service = TransactionService(db)
        
        # Преобразование date в datetime для совместимости с базой данных
        start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None
        
        # Получение финансовой сводки
        summary = transaction_service.get_financial_summary(
            user_id=current_user.id,
            start_date=start_datetime,
            end_date=end_datetime
        )
        
        return summary
    except Exception as e:
        logger.error(f"Error getting financial summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@transaction_router.get("/analytics/by-category")
def get_category_summary(
    start_date: Optional[date] = Query(None, description="Start date for summary"),
    end_date: Optional[date] = Query(None, description="End date for summary"),
    type: TransactionType = Query(None, description="Transaction type (income/expense)"),
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get summary grouped by category
    - Shows spending/income distribution by category
    - Can be filtered by date range and type
    """
    try:
        transaction_service = TransactionService(db)
        
        # Преобразование date в datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None
        
        # Получение сводки по категориям
        summary = transaction_service.get_category_summary(
            user_id=current_user.id,
            start_date=start_datetime,
            end_date=end_datetime,
            transaction_type=type
        )
        
        return summary
    except Exception as e:
        logger.error(f"Error getting category summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@transaction_router.get("/analytics/monthly")
def get_monthly_statistics(
    year: int = Query(None, description="Year for statistics"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month for statistics"),
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get monthly statistics
    - Shows income, expense, balance for each month
    - Can be filtered by specific year or month
    """
    try:
        transaction_service = TransactionService(db)
        
        # Если год не указан, используем текущий год
        if year is None:
            year = datetime.now().year
        
        # Получение ежемесячной статистики
        statistics = transaction_service.get_monthly_statistics(
            user_id=current_user.id,
            year=year,
            month=month
        )
        
        return statistics
    except Exception as e:
        logger.error(f"Error getting monthly statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@transaction_router.get("/analytics/top-categories")
def get_top_categories(
    limit: int = Query(5, ge=1, le=20, description="Number of top categories to return"),
    type: TransactionType = Query(TransactionType.EXPENSE, description="Transaction type (income/expense)"),
    period_days: Optional[int] = Query(30, ge=1, description="Period in days to analyze"),
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top categories by amount
    - Shows most significant spending/income categories
    - Can be limited to recent period
    """
    try:
        transaction_service = TransactionService(db)
        
        # Получение топ-категорий
        top_categories = transaction_service.get_top_categories(
            user_id=current_user.id,
            limit=limit,
            transaction_type=type,
            period_days=period_days
        )
        
        return top_categories
    except Exception as e:
        logger.error(f"Error getting top categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@transaction_router.get("/recent")
def get_recent_transactions(
    limit: int = Query(10, ge=1, le=50, description="Number of recent transactions"),
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recent transactions
    - Returns most recent transactions for quick overview
    """
    try:
        transaction_service = TransactionService(db)
        
        # Получение последних транзакций
        recent_transactions = transaction_service.get_recent_transactions(
            user_id=current_user.id,
            limit=limit
        )
        
        return recent_transactions
    except Exception as e:
        logger.error(f"Error getting recent transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@transaction_router.get("/search")
def search_transactions(
    query: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search transactions by name
    - Case-insensitive search
    - Returns matching transactions
    """
    try:
        transaction_service = TransactionService(db)
        
        # Поиск транзакций по названию
        results = transaction_service.search_transactions(
            user_id=current_user.id,
            search_term=query,
            limit=limit
        )
        
        return results
    except Exception as e:
        logger.error(f"Error searching transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@transaction_router.get("/daily/{date}")
def get_daily_statistics(
    date: date = Query(..., description="Date for daily statistics"),
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily statistics
    - Shows income, expense, balance for specific day
    - Includes list of transactions for that day
    """
    try:
        transaction_service = TransactionService(db)
        
        # Получение статистики за день
        daily_stats = transaction_service.get_daily_statistics(
            user_id=current_user.id,
            date=date
        )
        
        return daily_stats
    except Exception as e:
        logger.error(f"Error getting daily statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )