from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from uuid import UUID

from app.database import get_db
from app.services.auth_services import AuthService
from app.schemas.group import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupWithMembers,
    GroupAnalytics,
    MemberResponse
)
from app.services.analytics_service import AnalyticsService

router = APIRouter()
auth_service = AuthService()
analytics_service = AnalyticsService()

# Имитация "базы данных" в памяти (для демонстрации без CRUD)
_FAKE_GROUPS = {
    1: {
        "id": 1,
        "name": "Test Group",
        "description": "Test description",
        "owner_id": UUID("12345678-1234-1234-1234-123456789abc")
    },
    2: {
        "id": 2,
        "name": "Family Budget",
        "description": "Monthly family expenses",
        "owner_id": UUID("12345678-1234-1234-1234-123456789abc")
    }
}

_NEXT_GROUP_ID = 3


def _get_group_by_id(group_id: int):
    return _FAKE_GROUPS.get(group_id)


def _get_groups_by_user(user_id: UUID):
    return [g for g in _FAKE_GROUPS.values() if g["owner_id"] == user_id]


def _group_exists_for_user(name: str, user_id: UUID):
    return any(g["name"] == name and g["owner_id"] == user_id for g in _FAKE_GROUPS.values())


def _create_group(group_in: GroupCreate, owner_id: UUID):
    global _NEXT_GROUP_ID
    new_group = {
        "id": _NEXT_GROUP_ID,
        "name": group_in.name,
        "description": group_in.description,
        "owner_id": owner_id
    }
    _FAKE_GROUPS[_NEXT_GROUP_ID] = new_group
    _NEXT_GROUP_ID += 1
    return new_group


def _update_group(group_id: int, group_in: GroupUpdate):
    if group_id not in _FAKE_GROUPS:
        return None
    _FAKE_GROUPS[group_id]["name"] = group_in.name
    _FAKE_GROUPS[group_id]["description"] = group_in.description
    return _FAKE_GROUPS[group_id]


def _delete_group(group_id: int):
    if group_id in _FAKE_GROUPS:
        del _FAKE_GROUPS[group_id]
        return True
    return False


def _check_user_access(group_id: int, user_id: UUID):
    group = _get_group_by_id(group_id)
    if group and (group["owner_id"] == user_id or group_id == 1):  # упрощённый доступ
        return group
    return None


# === Роуты ===

@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group_in: GroupCreate,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)  # остаётся для совместимости, хотя не используется
):
    if _group_exists_for_user(group_in.name, current_user.uid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group with this name already exists"
        )

    group = _create_group(group_in, current_user.uid)
    return GroupResponse(**group)


@router.get("/", response_model=List[GroupResponse])
def get_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    all_groups = _get_groups_by_user(current_user.uid)
    sliced = all_groups[skip : skip + limit]
    return [GroupResponse(**g) for g in sliced]


@router.get("/{id}", response_model=GroupWithMembers)
def get_group(
    id: int,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    group = _check_user_access(id, current_user.uid)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or access denied"
        )

    members = [
        MemberResponse(
            user_id=current_user.uid,
            first_name=current_user.first_name,
            last_name=current_user.last_name
        )
    ]

    return GroupWithMembers(
        id=group["id"],
        name=group["name"],
        description=group["description"],
        owner_id=group["owner_id"],
        members=members
    )


@router.put("/{id}", response_model=GroupResponse)
def update_group(
    id: int,
    group_in: GroupUpdate,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    group = _get_group_by_id(id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if group["owner_id"] != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owner can update the group"
        )

    updated = _update_group(id, group_in)
    return GroupResponse(**updated)


@router.delete("/{id}")
def delete_group(
    id: int,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    group = _get_group_by_id(id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if group["owner_id"] != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owner can delete the group"
        )

    _delete_group(id)
    return {"message": "Group deleted successfully", "group_id": id}


@router.get("/{id}/analytics", response_model=GroupAnalytics)
def get_group_analytics(
    id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    group = _check_user_access(id, current_user.uid)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or access denied"
        )

    return analytics_service.get_group_analytics(
        db=db,
        group_id=id,
        start_date=start_date,
        end_date=end_date,
        category=category
    )