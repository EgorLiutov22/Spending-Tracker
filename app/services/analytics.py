from datetime import datetime, date
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case, extract
from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.models.user import User
from app.models.group import Group, user_group_association
from app.schemas.analytic_schema import CategorySummary, DailySummary


class AnalyticsService:

    @staticmethod
    async def get_overview(
            db: AsyncSession,
            user: User,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> dict:

        if not start_date:
            start_date = date(1970, 1, 1)
        if not end_date:
            end_date = date.today()

        stmt = select(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount)), else_=0),
                          0).label("income"),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount)), else_=0),
                          0).label("expense")
        ).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
        )

        result = await db.execute(stmt)
        income, expense = result.fetchone()
        return {
            "balance": float(income - expense),
            "total_income": float(income),
            "total_expense": float(expense),
            "period_start": start_date,
            "period_end": end_date
        }

    @staticmethod
    async def get_by_category(
            db: AsyncSession,
            user: User,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> List[CategorySummary]:
        if not start_date:
            start_date = date(1970, 1, 1)
        if not end_date:
            end_date = date.today()

        total_expense_subq = select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
        ).scalar_subquery()

        stmt = select(
            Category.name,
            Category.type,
            func.sum(Transaction.amount).label("total"),
            (func.sum(Transaction.amount) / total_expense_subq * 100).label("percentage")
        ).select_from(Transaction).join(Category).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
        ).group_by(Category.id, Category.name, Category.type).order_by(func.sum(Transaction.amount).desc())

        result = await db.execute(stmt)
        rows = result.fetchall()
        return [
            CategorySummary(
                category_name=row.name,
                category_type=row.type.value,
                total_amount=float(row.total),
                percentage=float(row.percentage or 0)
            )
            for row in rows
        ]

    @staticmethod
    async def get_by_date(
            db: AsyncSession,
            user: User,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            group_by: str = "day"
    ) -> List[DailySummary]:
        if not start_date:
            start_date = date(1970, 1, 1)
        if not end_date:
            end_date = date.today()

        if group_by == "week":
            date_part = func.date_trunc("week", Transaction.date)
        elif group_by == "month":
            date_part = func.date_trunc("month", Transaction.date)
        else:
            date_part = func.date(Transaction.date)

        stmt = select(
            func.date(date_part).label("date"),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount)), else_=0),
                          0).label("income"),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount)), else_=0),
                          0).label("expense")
        ).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
        ).group_by(date_part).order_by(date_part)

        result = await db.execute(stmt)
        rows = result.fetchall()
        return [
            DailySummary(
                date=row.date,
                income=float(row.income),
                expense=float(row.expense),
                balance=float(row.income - row.expense)
            )
            for row in rows
        ]
