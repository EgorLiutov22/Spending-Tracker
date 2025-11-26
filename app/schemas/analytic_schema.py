from datetime import date as DateType
from typing import List, Optional
from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    balance: float
    total_income: float
    total_expense: float
    period_start: date
    period_end: date


class CategorySummary(BaseModel):
    category_name: str
    category_type: str  # "income" or "expense"
    total_amount: float
    percentage: float


class DailySummary(BaseModel):
    date: DateType
    income: float
    expense: float
    balance: float


class ExportParams(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category_id: Optional[int] = None
    group_id: Optional[int] = None
    format: str = "csv"  # "csv" or "xlsx"
