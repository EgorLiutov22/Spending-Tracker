import pytest
from sqlalchemy.exc import IntegrityError
from app.models.group import Group, user_group_association


class TestGroupModel:
    """Тесты для модели Group"""
    
    def test_create_group(self, create_group):
        """Тест создания группы"""
        group = create_group(
            name="Семейный бюджет",
            description="Группа для учета семейных финансов"
        )
        
        assert group.id is not None
        assert group.name == "Семейный бюджет"
        assert group.description == "Группа для учета семейных финансов"
        assert group.owner_id is not None
    
    def test_group_repr(self, create_group):
        """Тест строкового представления"""
        group = create_group(name="Тестовая группа")
        
        expected_repr = f"<Group(id={group.id}, name='Тестовая группа', owner_id={group.owner_id})>"
        assert repr(group) == expected_repr
    
    def test_group_required_fields(self, db_session, create_user):
        """Тест обязательных полей"""
        user = create_user()
        
        # Без name
        group1 = Group(
            description="Без имени",
            owner_id=user.id
        )
        db_session.add(group1)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        
        # Без owner_id
        group2 = Group(
            name="Группа",
            description="Без владельца"
        )
        db_session.add(group2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
    
    def test_group_owner_relationship(self, create_group):
        """Тест связи с владельцем"""
        group = create_group()
        
        assert group.owner.id == group.owner_id
        assert group in group.owner.owned_groups
    
    def test_group_members_relationship(self, db_session, create_user, create_group):
        """Тест связи с участниками"""
        owner = create_user(email="owner@example.com")
        member1 = create_user(email="member1@example.com")
        member2 = create_user(email="member2@example.com")
        
        group = create_group(owner_id=owner.id)
        
        # Добавляем участников
        group.members.extend([member1, member2])
        db_session.commit()
        
        # Проверяем, что владелец тоже считается участником?
        # Это зависит от бизнес-логики. Обычно владелец автоматически участник.
        # Если нет, то нужно добавить:
        # group.members.append(owner)
        
        assert len(group.members) == 2
        assert member1 in group.members
        assert member2 in group.members
        
        # Проверяем обратную связь
        assert group in member1.groups
        assert group in member2.groups
    
    def test_group_transactions_relationship(self, db_session, create_group, create_transaction):
        """Тест связи с транзакциями"""
        group = create_group()
        
        # Создаем транзакции в группе
        transaction1 = create_transaction(
            user_id=group.owner_id,
            group_id=group.id
        )
        
        transaction2 = create_transaction(
            user_id=group.owner_id,
            group_id=group.id
        )
        
        assert len(group.transactions) == 2
        assert transaction1 in group.transactions
        assert transaction2 in group.transactions
        
        # Проверяем обратную связь
        assert transaction1.group.id == group.id
        assert transaction2.group.id == group.id
    
    def test_association_table(self, db_session, create_user, create_group):
        """Тест ассоциативной таблицы"""
        user1 = create_user(email="user1@example.com")
        user2 = create_user(email="user2@example.com")
        group1 = create_group(owner_id=user1.id)
        group2 = create_group(owner_id=user2.id)
        
        # Добавляем пользователей в группы
        group1.members.append(user1)
        group1.members.append(user2)
        group2.members.append(user1)
        
        db_session.commit()
        
        # Проверяем связи через ассоциативную таблицу
        stmt = db_session.query(user_group_association)
        associations = db_session.execute(stmt).fetchall()
        
        # Должно быть 3 записи:
        # 1. user1 в group1
        # 2. user2 в group1
        # 3. user1 в group2
        assert len(associations) == 3
        
        # Проверяем конкретные связи
        user1_groups = [g.id for g in user1.groups]
        assert group1.id in user1_groups
        assert group2.id in user1_groups
        
        user2_groups = [g.id for g in user2.groups]
        assert group1.id in user2_groups
        assert group2.id not in user2_groups
    
    def test_cascade_delete_owner(self, db_session, create_group):
        """Тест удаления владельца группы"""
        group = create_group()
        group_id = group.id
        owner_id = group.owner_id
        
        # Удаляем владельца
        from app.models.user import User
        owner = db_session.query(User).filter_by(id=owner_id).first()
        db_session.delete(owner)
        db_session.commit()
        
        # Группа должна быть удалена из-за ondelete='CASCADE' в owner_id
        group_after = db_session.query(Group).filter_by(id=group_id).first()
        assert group_after is None
    
    def test_string_length_constraint(self, db_session, create_user):
        """Тест ограничения длины названия группы"""
        user = create_user()
        
        # Название длиной 100 символов (максимум)
        long_name = "Г" * 100
        group = Group(
            name=long_name,
            owner_id=user.id
        )
        
        db_session.add(group)
        db_session.commit()
        
        assert group.name == long_name
        
        # Очистка
        db_session.delete(group)
        db_session.commit()