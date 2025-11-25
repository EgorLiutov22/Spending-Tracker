from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.services.auth_services import AuthService
from app.services.group_service import group_service
from app.services.analytics_service import analytics_service


# Временные схемы для групп (добавьте в app/schemas/group.py)
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


# Временный CRUD для групп (создайте app/crud/crud_group.py)
class GroupCRUD:
    @staticmethod
    def get_by_name_and_owner(db: Session, name: str, owner_id: UUID):
        # Временная реализация
        return None

    @staticmethod
    def create_with_owner(db: Session, obj_in: GroupCreate, owner_id: UUID):
        # Временная реализация
        return GroupResponse(
            id=1,
            name=obj_in.name,
            description=obj_in.description,
            owner_id=owner_id
        )

    @staticmethod
    def get_multi_by_user(db: Session, user_id: UUID, skip: int = 0, limit: int = 100):
        # Временная реализация
        return [
            GroupResponse(
                id=1,
                name="Family Budget",
                description="Monthly family expenses",
                owner_id=user_id
            ),
            GroupResponse(
                id=2,
                name="Trip to Mountains",
                description="Weekend trip expenses",
                owner_id=user_id
            ),
        ]

    @staticmethod
    def get(db: Session, id: int):
        # Временная реализация
        if id == 1:
            return GroupResponse(
                id=1,
                name="Test Group",
                description="Test description",
                owner_id=UUID("12345678-1234-1234-1234-123456789abc")
            )
        return None

    @staticmethod
    def update(db: Session, db_obj: GroupResponse, obj_in: GroupUpdate):
        # Временная реализация
        if hasattr(db_obj, 'name'):
            db_obj.name = obj_in.name
        if hasattr(db_obj, 'description'):
            db_obj.description = obj_in.description
        return db_obj

    @staticmethod
    def remove(db: Session, id: int):
        # Временная реализация
        return True


# Инициализация CRUD и AuthService
group_crud = GroupCRUD()
auth_service = AuthService()

router = APIRouter()


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
        group_in: GroupCreate,
        current_user=Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Create a new group
    - Creates group and automatically adds creator as member
    - Only authenticated users can create groups
    """
    # Проверяем, нет ли группы с таким названием у пользователя
    existing_group = group_crud.get_by_name_and_owner(
        db, name=group_in.name, owner_id=current_user.uid
    )
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group with this name already exists"
        )

    # Создаем группу
    group = group_crud.create_with_owner(
        db=db,
        obj_in=group_in,
        owner_id=current_user.uid
    )

    return group


@router.get("/", response_model=List[GroupResponse])
def get_groups(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=100, description="Number of records to return"),
        current_user=Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Get list of user's groups with pagination
    - Returns groups where user is owner OR member
    - Includes pagination for large datasets
    """
    groups = group_crud.get_multi_by_user(
        db=db,
        user_id=current_user.uid,
        skip=skip,
        limit=limit
    )
    return groups


@router.get("/{id}", response_model=GroupWithMembers)
def get_group(
        id: int,
        current_user=Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Get specific group with members information
    - User must be a member of the group to access
    - Returns detailed group info with member list
    """
    # Проверяем, что пользователь имеет доступ к группе
    group = group_service.get_group_with_access_check(
        db=db,
        group_id=id,
        user_id=current_user.uid
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or access denied"
        )

    # Создаем ответ с участниками
    members = [
        MemberResponse(
            user_id=current_user.uid,
            first_name=current_user.first_name,
            last_name=current_user.last_name
        )
    ]

    group_with_members = GroupWithMembers(
        id=group.id,
        name=group.name,
        description=group.description,
        owner_id=group.owner_id,
        members=members
    )

    return group_with_members


@router.put("/{id}", response_model=GroupResponse)
def update_group(
        id: int,
        group_in: GroupUpdate,
        current_user=Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Update group information
    - Only group owner can update group details
    - Validates that user is the owner
    """
    # Проверяем права на редактирование
    group = group_crud.get(db, id=id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    if group.owner_id != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owner can update the group"
        )

    # Обновляем группу
    updated_group = group_crud.update(db, db_obj=group, obj_in=group_in)
    return updated_group


@router.delete("/{id}")
def delete_group(
        id: int,
        current_user=Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Delete group (only by owner)
    - Only group owner can delete the group
    - All group transactions and member associations are deleted (cascade)
    """
    # Проверяем права на удаление
    group = group_crud.get(db, id=id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    if group.owner_id != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owner can delete the group"
        )

    # Удаляем группу
    group_crud.remove(db, id=id)

    return {
        "message": "Group deleted successfully",
        "group_id": id
    }


@router.get("/{id}/analytics", response_model=GroupAnalytics)
def get_group_analytics(
        id: int,
        start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
        end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
        category: Optional[str] = Query(None, description="Filter by category"),
        current_user=Depends(auth_service.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Get analytics for specific group
    - User must be a member of the group
    - Returns financial analytics with filters
    - Includes category breakdown and member contributions
    """
    # Проверяем доступ к группе
    group = group_service.get_group_with_access_check(
        db=db,
        group_id=id,
        user_id=current_user.uid
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or access denied"
        )

    # Получаем аналитику
    analytics = analytics_service.get_group_analytics(
        db=db,
        group_id=id,
        start_date=start_date,
        end_date=end_date,
        category=category
    )

    return analytics