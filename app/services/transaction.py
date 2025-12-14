from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func, select, extract, text
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
import logging

from app.models.transaction import Transaction
from app.models.category import Category
from app.models.user import User
from app.models.group import Group
from app.models.enums import TransactionType
from app.schemas.transaction import TransactionCreate, TransactionUpdate

logger = logging.getLogger(__name__)


class TransactionService:
    """Сервис для работы с транзакциями"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== CRUD ОПЕРАЦИИ ==========
    
    def create_transaction(self, transaction_data: TransactionCreate, user_id: int) -> Transaction:
        """
        Создание новой транзакции
        """
        try:
            # Проверка существования категории
            category = self.db.query(Category).filter(
                and_(
                    Category.id == transaction_data.category_id,
                    Category.user_id == user_id
                )
            ).first()
            
            if not category:
                raise ValueError(f"Category with id {transaction_data.category_id} not found")
            
            # Проверка группы, если указана
            if transaction_data.group_id:
                group = self.db.query(Group).filter(
                    and_(
                        Group.id == transaction_data.group_id,
                        Group.users.any(User.id == user_id)
                    )
                ).first()
                
                if not group:
                    raise ValueError(f"Group with id {transaction_data.group_id} not found or access denied")
            
            db_transaction = Transaction(
                name=transaction_data.name,
                type=transaction_data.type,
                category_id=transaction_data.category_id,
                amount=Decimal(str(transaction_data.amount)),
                date=transaction_data.date or datetime.now(),
                user_id=user_id,
                group_id=transaction_data.group_id
            )
            
            self.db.add(db_transaction)
            self.db.commit()
            self.db.refresh(db_transaction)
            
            logger.info(f"Transaction created: {db_transaction.id} for user {user_id}")
            return db_transaction
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating transaction: {str(e)}")
            raise
    
    def get_transaction(self, transaction_id: int, user_id: int) -> Optional[Transaction]:
        """
        Получение транзакции по ID с проверкой прав доступа
        """
        return self.db.query(Transaction).filter(
            and_(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id
            )
        ).first()
    
    def get_user_transactions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        category_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        type: Optional[TransactionType] = None,
        group_id: Optional[int] = None,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> Tuple[List[Transaction], int]:
        """
        Получение списка транзакций пользователя с пагинацией и фильтрами
        Возвращает (список транзакций, общее количество)
        """
        # Базовый запрос
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        # Применение фильтров
        if category_id is not None:
            query = query.filter(Transaction.category_id == category_id)
        
        if start_date is not None:
            query = query.filter(Transaction.date >= start_date)
        
        if end_date is not None:
            query = query.filter(Transaction.date <= end_date)
        
        if type is not None:
            query = query.filter(Transaction.type == type)
        
        if group_id is not None:
            query = query.filter(Transaction.group_id == group_id)
        
        # Получение общего количества (для пагинации)
        total_count = query.count()
        
        # Сортировка
        sort_column = {
            "date": Transaction.date,
            "amount": Transaction.amount,
            "name": Transaction.name
        }.get(sort_by, Transaction.date)
        
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # Пагинация
        transactions = query.offset(skip).limit(limit).all()
        
        return transactions, total_count
    
    def update_transaction(
        self,
        transaction_id: int,
        user_id: int,
        update_data: TransactionUpdate
    ) -> Optional[Transaction]:
        """
        Обновление транзакции
        """
        transaction = self.get_transaction(transaction_id, user_id)
        if not transaction:
            return None
        
        try:
            update_dict = update_data.dict(exclude_unset=True)
            
            # Валидация обновляемых полей
            if 'category_id' in update_dict:
                category = self.db.query(Category).filter(
                    and_(
                        Category.id == update_dict['category_id'],
                        Category.user_id == user_id
                    )
                ).first()
                
                if not category:
                    raise ValueError(f"Category with id {update_dict['category_id']} not found")
            
            if 'group_id' in update_dict and update_dict['group_id'] is not None:
                group = self.db.query(Group).filter(
                    and_(
                        Group.id == update_dict['group_id'],
                        Group.users.any(User.id == user_id)
                    )
                ).first()
                
                if not group:
                    raise ValueError(f"Group with id {update_dict['group_id']} not found or access denied")
            
            # Обновление полей
            for field, value in update_dict.items():
                if field == 'amount':
                    value = Decimal(str(value))
                setattr(transaction, field, value)
            
            transaction.date = transaction.date or datetime.now()
            
            self.db.commit()
            self.db.refresh(transaction)
            
            logger.info(f"Transaction updated: {transaction_id}")
            return transaction
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating transaction {transaction_id}: {str(e)}")
            raise
    
    def delete_transaction(self, transaction_id: int, user_id: int) -> bool:
        """
        Удаление транзакции
        """
        transaction = self.get_transaction(transaction_id, user_id)
        if not transaction:
            return False
        
        try:
            self.db.delete(transaction)
            self.db.commit()
            logger.info(f"Transaction deleted: {transaction_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting transaction {transaction_id}: {str(e)}")
            raise
    
    # ========== АНАЛИТИКА ==========
    
    def get_category_summary(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        transaction_type: Optional[TransactionType] = None
    ) -> List[Dict[str, Any]]:
        """
        Сводка по категориям
        """
        query = self.db.query(
            Transaction.category_id,
            Category.name.label("category_name"),
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("transaction_count")
        ).join(
            Category, Transaction.category_id == Category.id
        ).filter(
            Transaction.user_id == user_id
        )
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        if transaction_type:
            query = query.filter(Transaction.type == transaction_type)
        
        results = query.group_by(
            Transaction.category_id, Category.name
        ).order_by(desc("total_amount")).all()
        
        return [
            {
                "category_id": r.category_id,
                "category_name": r.category_name,
                "total_amount": float(r.total_amount) if r.total_amount else 0.0,
                "transaction_count": r.transaction_count,
                "percentage": 0.0  # Рассчитывается отдельно
            }
            for r in results
        ]
    
    def get_financial_summary(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Общая финансовая сводка (доходы, расходы, баланс)
        """
        # Доходы
        income_query = self.db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.INCOME
            )
        )
        
        # Расходы
        expense_query = self.db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE
            )
        )
        
        # Количество транзакций
        count_query = self.db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_id
        )
        
        # Фильтрация по дате
        if start_date:
            income_query = income_query.filter(Transaction.date >= start_date)
            expense_query = expense_query.filter(Transaction.date >= start_date)
            count_query = count_query.filter(Transaction.date >= start_date)
        
        if end_date:
            income_query = income_query.filter(Transaction.date <= end_date)
            expense_query = expense_query.filter(Transaction.date <= end_date)
            count_query = count_query.filter(Transaction.date <= end_date)
        
        total_income = income_query.scalar() or Decimal('0')
        total_expense = expense_query.scalar() or Decimal('0')
        transaction_count = count_query.scalar() or 0
        
        return {
            "total_income": float(total_income),
            "total_expense": float(total_expense),
            "balance": float(total_income - total_expense),
            "transaction_count": transaction_count,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
    
    def get_monthly_statistics(
        self,
        user_id: int,
        year: int,
        month: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Статистика по месяцам
        """
        query = self.db.query(
            extract('year', Transaction.date).label("year"),
            extract('month', Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("amount"),
            func.count(Transaction.id).label("count")
        ).filter(
            and_(
                Transaction.user_id == user_id,
                extract('year', Transaction.date) == year
            )
        )
        
        if month:
            query = query.filter(extract('month', Transaction.date) == month)
        
        results = query.group_by(
            extract('year', Transaction.date),
            extract('month', Transaction.date),
            Transaction.type
        ).order_by(
            extract('year', Transaction.date),
            extract('month', Transaction.date)
        ).all()
        
        # Форматирование результатов
        monthly_data = {}
        for r in results:
            key = f"{int(r.year)}-{int(r.month):02d}"
            if key not in monthly_data:
                monthly_data[key] = {
                    "year": int(r.year),
                    "month": int(r.month),
                    "income": 0.0,
                    "expense": 0.0,
                    "balance": 0.0
                }
            
            if r.type == TransactionType.INCOME:
                monthly_data[key]["income"] = float(r.amount)
            else:
                monthly_data[key]["expense"] = float(r.amount)
        
        # Расчет баланса
        for data in monthly_data.values():
            data["balance"] = data["income"] - data["expense"]
        
        return list(monthly_data.values())
    
    def get_top_categories(
        self,
        user_id: int,
        limit: int = 5,
        transaction_type: TransactionType = TransactionType.EXPENSE,
        period_days: Optional[int] = 30
    ) -> List[Dict[str, Any]]:
        """
        Топ категорий по расходам/доходам
        """
        query = self.db.query(
            Category.name,
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("transaction_count")
        ).join(
            Category, Transaction.category_id == Category.id
        ).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == transaction_type
            )
        )
        
        if period_days:
            cutoff_date = datetime.now() - timedelta(days=period_days)
            query = query.filter(Transaction.date >= cutoff_date)
        
        results = query.group_by(Category.name).order_by(
            desc("total_amount")
        ).limit(limit).all()
        
        return [
            {
                "category_name": r.name,
                "total_amount": float(r.total_amount) if r.total_amount else 0.0,
                "transaction_count": r.transaction_count,
                "average_amount": float(r.total_amount / r.transaction_count) if r.transaction_count > 0 else 0.0
            }
            for r in results
        ]
    
    # ========== ГРУППОВЫЕ ОПЕРАЦИИ ==========
    
    def get_group_transactions(
        self,
        group_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Transaction], int]:
        """
        Получение транзакций группы
        """
        # Проверка, что пользователь состоит в группе
        group = self.db.query(Group).filter(
            and_(
                Group.id == group_id,
                Group.users.any(User.id == user_id)
            )
        ).first()
        
        if not group:
            raise ValueError("Group not found or access denied")
        
        query = self.db.query(Transaction).filter(
            Transaction.group_id == group_id
        )
        
        total_count = query.count()
        transactions = query.order_by(
            desc(Transaction.date)
        ).offset(skip).limit(limit).all()
        
        return transactions, total_count
    
    def get_group_summary(self, group_id: int, user_id: int) -> Dict[str, Any]:
        """
        Сводка по группе
        """
        # Проверка доступа
        group = self.db.query(Group).filter(
            and_(
                Group.id == group_id,
                Group.users.any(User.id == user_id)
            )
        ).first()
        
        if not group:
            raise ValueError("Group not found or access denied")
        
        # Статистика по группе
        result = self.db.query(
            Transaction.type,
            func.sum(Transaction.amount).label("amount"),
            func.count(Transaction.id).label("count"),
            User.username.label("username")
        ).join(
            User, Transaction.user_id == User.id
        ).filter(
            Transaction.group_id == group_id
        ).group_by(
            Transaction.type, User.username
        ).all()
        
        # Форматирование результатов
        summary = {
            "group_id": group_id,
            "group_name": group.name,
            "members": [],
            "total_income": 0.0,
            "total_expense": 0.0,
            "balance": 0.0
        }
        
        user_stats = {}
        for r in result:
            username = r.username
            if username not in user_stats:
                user_stats[username] = {"income": 0.0, "expense": 0.0}
            
            if r.type == TransactionType.INCOME:
                user_stats[username]["income"] += float(r.amount)
                summary["total_income"] += float(r.amount)
            else:
                user_stats[username]["expense"] += float(r.amount)
                summary["total_expense"] += float(r.amount)
        
        summary["balance"] = summary["total_income"] - summary["total_expense"]
        summary["members"] = [
            {
                "username": username,
                "income": stats["income"],
                "expense": stats["expense"],
                "balance": stats["income"] - stats["expense"]
            }
            for username, stats in user_stats.items()
        ]
        
        return summary
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========
    
    def get_recent_transactions(self, user_id: int, limit: int = 10) -> List[Transaction]:
        """
        Последние транзакции пользователя
        """
        return self.db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(
            desc(Transaction.date)
        ).limit(limit).all()
    
    def search_transactions(
        self,
        user_id: int,
        search_term: str,
        limit: int = 50
    ) -> List[Transaction]:
        """
        Поиск транзакций по названию
        """
        return self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.name.ilike(f"%{search_term}%")
            )
        ).order_by(
            desc(Transaction.date)
        ).limit(limit).all()
    
    def get_daily_statistics(
        self,
        user_id: int,
        date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Статистика за день
        """
        target_date = date or datetime.now().date()
        
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        daily_transactions = self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.date >= start_datetime,
                Transaction.date <= end_datetime
            )
        ).all()
        
        total_income = sum(
            float(t.amount) for t in daily_transactions 
            if t.type == TransactionType.INCOME
        )
        
        total_expense = sum(
            float(t.amount) for t in daily_transactions 
            if t.type == TransactionType.EXPENSE
        )
        
        return {
            "date": target_date.isoformat(),
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
            "transaction_count": len(daily_transactions),
            "transactions": daily_transactions
        }
    
    def import_transactions(
        self,
        user_id: int,
        transactions_data: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        Импорт транзакций из внешнего источника
        Возвращает (количество успешно импортированных, количество с ошибками)
        """
        success_count = 0
        error_count = 0
        
        for data in transactions_data:
            try:
                transaction = TransactionCreate(**data)
                self.create_transaction(transaction, user_id)
                success_count += 1
            except Exception as e:
                logger.error(f"Error importing transaction: {str(e)}")
                error_count += 1
        
        return success_count, error_count
    
    def cleanup_old_transactions(self, user_id: int, days: int = 365) -> int:
        """
        Удаление старых транзакций (опционально)
        Возвращает количество удаленных транзакций
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted_count = self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.date < cutoff_date
            )
        ).delete(synchronize_session=False)
        
        self.db.commit()
        logger.info(f"Cleaned up {deleted_count} old transactions for user {user_id}")
        
        return deleted_count