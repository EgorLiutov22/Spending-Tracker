from datetime import date
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.transaction import Transaction
from app.models.enums import TransactionType
from app.models.category import Category
from app.models.user import User
from app.models.group import Group
from app.schemas.analytic_schema import CategorySummary, DailySummary
from app.schemas.group import GroupAnalytics, CategoryBreakdown, MemberContribution


class AnalyticsService:

    # === ЛИЧНАЯ АНАЛИТИКА  ===
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
            func.coalesce(func.sum(func.case((Transaction.type == TransactionType.INCOME, Transaction.amount)), else_=0),
                          0).label("income"),
            func.coalesce(func.sum(func.case((Transaction.type == TransactionType.EXPENSE, Transaction.amount)), else_=0),
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
            func.coalesce(func.sum(func.case((Transaction.type == TransactionType.INCOME, Transaction.amount)), else_=0),
                          0).label("income"),
            func.coalesce(func.sum(func.case((Transaction.type == TransactionType.EXPENSE, Transaction.amount)), else_=0),
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

    # === ГРУППОВАЯ АНАЛИТИКА ===
    @staticmethod
    async def get_group_analytics(
        db: AsyncSession,
        group_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None
    ) -> GroupAnalytics:
        # Проверка существования группы и доступа через JOIN в основном запросе
        base_query = (
            select(Transaction)
            .join(Transaction.user)
            .join(Transaction.category)
            .where(Transaction.group_id == group_id)
        )
        if start_date:
            base_query = base_query.where(Transaction.date >= start_date)
        if end_date:
            base_query = base_query.where(Transaction.date <= end_date)
        if category:
            base_query = base_query.where(Category.name == category)

        result = await db.execute(base_query)
        transactions = result.scalars().all()

        if not transactions:
            # Получаем участников для member_count
            group_result = await db.execute(select(Group).where(Group.id == group_id))
            group = group_result.scalar_one_or_none()
            member_count = len(group.members) if group else 0
            return GroupAnalytics(
                total_expenses=0.0,
                total_income=0.0,
                balance=0.0,
                member_count=member_count,
                period_start=start_date,
                period_end=end_date,
                category_breakdown=[],
                member_contributions=[]
            )

        total_income = sum(t.amount for t in transactions if t.type == TransactionType.INCOME)
        total_expenses = sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE)
        balance = total_income - total_expenses

        # Разбивка по категориям
        cat_totals = {}
        for t in transactions:
            name = t.category.name if t.category else "Uncategorized"
            cat_totals[name] = cat_totals.get(name, 0) + float(t.amount)
        total_for_pct = total_expenses or 1.0
        category_breakdown = [
            CategoryBreakdown(
                category=cat,
                amount=amt,
                percentage=round(amt / total_for_pct * 100, 1)
            )
            for cat, amt in cat_totals.items()
        ]

        # Вклад участников
        user_totals = {}
        for t in transactions:
            uid = t.user.id
            if uid not in user_totals:
                user_totals[uid] = {
                    "user_id": uid,
                    "first_name": t.user.first_name,
                    "last_name": t.user.last_name,
                    "total": 0.0
                }
            user_totals[uid]["total"] += float(t.amount)

        total_contrib = sum(v["total"] for v in user_totals.values()) or 1.0
        member_contributions = [
            MemberContribution(
                user_id=v["user_id"],  # ← int, не UUID!
                first_name=v["first_name"],
                last_name=v["last_name"],
                total_contributed=v["total"],
                percentage=round(v["total"] / total_contrib * 100, 1)
            )
            for v in user_totals.values()
        ]

        # Member count
        group_result = await db.execute(select(Group).where(Group.id == group_id))
        group = group_result.scalar_one_or_none()
        member_count = len(group.members) if group else len(member_contributions)

        return GroupAnalytics(
            total_expenses=float(total_expenses),
            total_income=float(total_income),
            balance=float(balance),
            member_count=member_count,
            period_start=start_date,
            period_end=end_date,
            category_breakdown=category_breakdown,
            member_contributions=member_contributions
        )