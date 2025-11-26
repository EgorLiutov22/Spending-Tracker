from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.analytics import AnalyticsService
from app.schemas.analytics import AnalyticsOverview, CategorySummary, DailySummary, ExportParams
from app.utils.export import export_to_csv, export_to_xlsx

from app.utils.export import get_exporter

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    return await AnalyticsService.get_overview(db, current_user, start_date, end_date)


@router.get("/by-category", response_model=List[CategorySummary])
async def get_by_category(
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    return await AnalyticsService.get_by_category(db, current_user, start_date, end_date)


@router.get("/by-date", response_model=List[DailySummary])
async def get_by_date(
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None),
        group_by: str = Query("day", regex="^(day|week|month)$"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    return await AnalyticsService.get_by_date(db, current_user, start_date, end_date, group_by)


@router.get("/export")
async def export_transactions(
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None),
        category_id: Optional[int] = Query(None),
        group_id: Optional[int] = Query(None),
        format: str = Query("csv", regex="^(csv|xlsx)$"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    stmt = select(Transaction).where(Transaction.user_id == current_user.id)
    if start_date:
        stmt = stmt.where(Transaction.date >= start_date)
    if end_date:
        stmt = stmt.where(Transaction.date <= end_date)
    if category_id:
        stmt = stmt.where(Transaction.category_id == category_id)

    result = await db.execute(stmt)
    transactions = result.scalars().all()

    data = [t.to_dict() for t in transactions]

    exporter = get_exporter(format)
    return exporter.export(data)