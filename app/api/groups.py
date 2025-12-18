# app/api/groups.py
from sqlalchemy.orm import joinedload
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.group import Group
from app.models.transaction import Transaction
from app.schemas.group import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupWithMembers,
    GroupAnalytics,
    MemberResponse,
)
from app.services.analytics import AnalyticsService


router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_in: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Проверка дубликата по имени у пользователя
    result = await db.execute(
        select(Group).where(
            Group.name == group_in.name,
            Group.owner_id == current_user.id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group with this name already exists"
        )

    new_group = Group(
        name=group_in.name,
        description=group_in.description,
        owner_id=current_user.id
    )
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)

    # Автоматически добавляем владельца в участники
    # SQLAlchemy many-to-many
    new_group.members.append(current_user)
    await db.commit()

    return GroupResponse.model_validate(new_group)


@router.get("/", response_model=List[GroupResponse])
async def get_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Группы, которыми владеет пользователь или в которых он состоит
    stmt = (
        select(Group)
        .where((Group.owner_id == current_user.id) | (Group.members.any(User.id == current_user.id)))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    groups = result.scalars().all()
    return [GroupResponse.model_validate(g) for g in groups]


@router.get("/{id}", response_model=GroupWithMembers)
async def get_group(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Проверяем доступ: владелец или участник
    result = await db.execute(
        select(Group)
        .options(joinedload(Group.members))  # Подгружаем участников
        .where(Group.id == id)
        .where((Group.owner_id == current_user.id) | (Group.members.any(User.id == current_user.id)))
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or access denied"
        )

    members = [
        MemberResponse(
            user_id=m.id,
            first_name=m.first_name,
            last_name=m.last_name
        )
        for m in group.members
    ]

    return GroupWithMembers(
        id=group.id,
        name=group.name,
        description=group.description,
        owner_id=group.owner_id,
        members=members
    )


@router.put("/{id}", response_model=GroupResponse)
async def update_group(
    id: int,
    group_in: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Group).where(Group.id == id, Group.owner_id == current_user.id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or you are not the owner"
        )

    group.name = group_in.name
    group.description = group_in.description
    await db.commit()
    await db.refresh(group)
    return GroupResponse.model_validate(group)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Group).where(Group.id == id, Group.owner_id == current_user.id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or you are not the owner"
        )

    await db.delete(group)
    await db.commit()
    return


@router.get("/{id}/analytics", response_model=GroupAnalytics)
async def get_group_analytics(
    id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Проверка доступа к группе
    result = await db.execute(
        select(Group)
        .where(Group.id == id)
        .where((Group.owner_id == current_user.id) | (Group.members.any(User.id == current_user.id)))
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or access denied"
        )

    return await AnalyticsService.get_group_analytics(
        db=db,
        group_id=id,
        start_date=start_date,
        end_date=end_date,
        category=category
    )