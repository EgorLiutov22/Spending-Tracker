from typing import List, Optional
from uuid import UUID
from datetime import date
from pydantic import BaseModel, ConfigDict


class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None


class GroupCreate(GroupBase):
    pass


class GroupUpdate(GroupBase):
    pass


class GroupResponse(GroupBase):
    id: int
    owner_id: UUID

    model_config = ConfigDict(from_attributes=True)


class MemberResponse(BaseModel):
    user_id: UUID
    first_name: str
    last_name: str

    model_config = ConfigDict(from_attributes=True)


class GroupWithMembers(GroupResponse):
    members: List[MemberResponse] = []


class CategoryBreakdown(BaseModel):
    category: str
    amount: float
    percentage: float


class MemberContribution(BaseModel):
    user_id: UUID
    first_name: str
    last_name: str
    total_contributed: float
    percentage: float


class GroupAnalytics(BaseModel):
    total_expenses: float = 0.0
    total_income: float = 0.0
    balance: float = 0.0
    member_count: int = 0
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    category_breakdown: List[CategoryBreakdown] = []
    member_contributions: List[MemberContribution] = []