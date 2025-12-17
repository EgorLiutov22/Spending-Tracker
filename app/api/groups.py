from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.group import Group, user_group_association
from app.models.transaction import Transaction, TransactionType
from app.schemas.group import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupWithMembers,
    GroupAnalytics,
    MemberResponse,
    CategoryBreakdown,
    MemberContribution
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_in: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую группу"""
    # Проверяем, существует ли группа с таким названием у пользователя
    stmt = select(Group).where(
        Group.name == group_in.name,
        Group.owner_id == current_user.id
    )
    result = await db.execute(stmt)
    existing_group = result.scalar_one_or_none()
    
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group with this name already exists"
        )
    
    # Создаем группу
    group = Group(
        name=group_in.name,
        description=group_in.description,
        owner_id=current_user.id
    )
    
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    return group


@router.get("/", response_model=List[GroupResponse])
async def get_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить список групп пользователя"""
    stmt = select(Group).where(
        Group.owner_id == current_user.id
    ).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    groups = result.scalars().all()
    
    return groups


@router.get("/{group_id}", response_model=GroupWithMembers)
async def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить информацию о группе"""
    stmt = select(Group).where(Group.id == group_id)
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Проверяем, является ли пользователь владельцем или участником
    if group.owner_id != current_user.id and current_user not in group.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Получаем список участников
    members = [
        MemberResponse(
            user_id=member.id,
            first_name=member.first_name,
            last_name=member.last_name
        )
        for member in group.members
    ]
    
    return GroupWithMembers(
        id=group.id,
        name=group.name,
        description=group.description,
        owner_id=group.owner_id,
        members=members
    )


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    group_in: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновить информацию о группе"""
    stmt = select(Group).where(Group.id == group_id)
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    if group.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owner can update the group"
        )
    
    # Обновляем поля
    update_data = group_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    
    await db.commit()
    await db.refresh(group)
    
    return group


@router.delete("/{group_id}", status_code=status.HTTP_200_OK)
async def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить группу"""
    stmt = select(Group).where(Group.id == group_id)
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    if group.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owner can delete the group"
        )
    
    await db.delete(group)
    await db.commit()
    
    return {"message": "Group deleted successfully", "group_id": group_id}


@router.post("/{group_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def add_member_to_group(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Добавить участника в группу"""
    stmt = select(Group).where(Group.id == group_id)
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    if group.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owner can add members"
        )
    
    # Получаем пользователя для добавления
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user_to_add = user_result.scalar_one_or_none()
    
    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Проверяем, не состоит ли уже пользователь в группе
    if user_to_add in group.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this group"
        )
    
    # Добавляем пользователя в группу
    group.members.append(user_to_add)
    await db.commit()
    
    return {"message": "Member added successfully"}


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_member_from_group(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить участника из группы"""
    stmt = select(Group).where(Group.id == group_id)
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    if group.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owner can remove members"
        )
    
    # Получаем пользователя для удаления
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user_to_remove = user_result.scalar_one_or_none()
    
    if not user_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Проверяем, состоит ли пользователь в группе
    if user_to_remove not in group.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of this group"
        )
    
    # Удаляем пользователя из группы
    group.members.remove(user_to_remove)
    await db.commit()
    
    return {"message": "Member removed successfully"}


@router.get("/{group_id}/analytics", response_model=GroupAnalytics)
async def get_group_analytics(
    group_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить аналитику по группе"""
    stmt = select(Group).where(Group.id == group_id)
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Проверяем доступ
    if group.owner_id != current_user.id and current_user not in group.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Получаем транзакции группы
    transaction_stmt = select(Transaction).where(Transaction.group_id == group_id)
    
    if start_date:
        transaction_stmt = transaction_stmt.where(Transaction.date >= start_date)
    if end_date:
        transaction_stmt = transaction_stmt.where(Transaction.date <= end_date)
    
    transaction_result = await db.execute(transaction_stmt)
    transactions = transaction_result.scalars().all()
    
    # Рассчитываем аналитику
    total_income = 0.0
    total_expenses = 0.0
    category_totals = {}
    member_totals = {}
    
    for transaction in transactions:
        amount = float(transaction.amount)
        
        # Суммируем доходы и расходы
        if transaction.type == TransactionType.INCOME:
            total_income += amount
        else:
            total_expenses += amount
        
        # Группируем по категориям
        if transaction.category and transaction.category.name:
            category_name = transaction.category.name
            if category_name not in category_totals:
                category_totals[category_name] = 0.0
            category_totals[category_name] += amount
        
        # Группируем по участникам
        user_id = transaction.user_id
        if user_id not in member_totals:
            # Получаем информацию о пользователе
            user_stmt = select(User).where(User.id == user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if user:
                member_totals[user_id] = {
                    "user_id": user_id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "total": 0.0
                }
        
        if user_id in member_totals:
            member_totals[user_id]["total"] += amount
    
    # Рассчитываем проценты для категорий
    total_amount = total_income + total_expenses
    category_breakdown = []
    
    for category_name, amount in category_totals.items():
        percentage = (amount / total_amount * 100) if total_amount > 0 else 0
        category_breakdown.append(
            CategoryBreakdown(
                category=category_name,
                amount=amount,
                percentage=percentage
            )
        )
    
    # Рассчитываем проценты для участников
    member_contributions = []
    
    for member_data in member_totals.values():
        percentage = (member_data["total"] / total_amount * 100) if total_amount > 0 else 0
        member_contributions.append(
            MemberContribution(
                user_id=member_data["user_id"],
                first_name=member_data["first_name"],
                last_name=member_data["last_name"],
                total_contributed=member_data["total"],
                percentage=percentage
            )
        )
    
    return GroupAnalytics(
        total_expenses=total_expenses,
        total_income=total_income,
        balance=total_income - total_expenses,
        member_count=len(group.members) + 1,  # +1 для владельца
        period_start=start_date,
        period_end=end_date,
        category_breakdown=category_breakdown,
        member_contributions=member_contributions
    )