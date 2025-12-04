import pytest
from sqlalchemy.exc import IntegrityError
from app.models.user import User


class TestUserModel:
    """Тесты для модели User"""
    
    def test_create_user(self, db_session, create_user):
        """Тест создания пользователя"""
        user = create_user(
            first_name="Иван",
            last_name="Иванов",
            email="ivan@example.com"
        )
        
        assert user.id is not None
        assert user.first_name == "Иван"
        assert user.last_name == "Иванов"
        assert user.email == "ivan@example.com"
        assert user.hashed_password == "hashed_password_123"
        assert user.is_active is True
        assert user.created_at is not None
    
    def test_user_get_full_name(self, create_user):
        """Тест метода get_full_name"""
        user = create_user(
            first_name="Мария",
            last_name="Петрова"
        )
        
        assert user.get_full_name() == "Мария Петрова"
    
    def test_user_repr(self, create_user):
        """Тест строкового представления"""
        user = create_user(email="test@example.com")
        
        expected_repr = f"<User(id={user.id}, email='test@example.com')>"
        assert repr(user) == expected_repr
    
    def test_email_uniqueness(self, db_session, create_user):
        """Тест уникальности email"""
        # Создаем первого пользователя
        user1 = create_user(email="duplicate@example.com")
        
        # Пытаемся создать второго с таким же email
        user2 = User(
            first_name="Второй",
            last_name="Пользователь",
            email="duplicate@example.com",
            hashed_password="hash2"
        )
        
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()
    
    def test_required_fields(self, db_session):
        """Тест обязательных полей"""
        # Тест без first_name
        user1 = User(
            last_name="Иванов",
            email="test1@example.com",
            hashed_password="hash"
        )
        db_session.add(user1)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        
        # Тест без last_name
        user2 = User(
            first_name="Иван",
            email="test2@example.com",
            hashed_password="hash"
        )
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        
        # Тест без email
        user3 = User(
            first_name="Иван",
            last_name="Иванов",
            hashed_password="hash"
        )
        db_session.add(user3)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
    
    def test_user_relationships(self, db_session, create_user, create_category, create_transaction, create_group):
        """Тест связей пользователя"""
        user = create_user()
        
        # Создаем категорию пользователя
        category = create_category(user_id=user.id)
        
        # Создаем транзакцию пользователя
        transaction = create_transaction(user_id=user.id, category_id=category.id)
        
        # Создаем группу, где пользователь - владелец
        group = create_group(owner_id=user.id)
        
        # Добавляем пользователя в группу как участника
        group.members.append(user)
        db_session.commit()
        
        # Проверяем связи
        assert len(user.categories) == 1
        assert user.categories[0].id == category.id
        
        assert len(user.transactions) == 1
        assert user.transactions[0].id == transaction.id
        
        assert len(user.owned_groups) == 1
        assert user.owned_groups[0].id == group.id
        
        assert len(user.groups) == 1
        assert user.groups[0].id == group.id
    
    def test_user_is_active_default(self, db_session):
        """Тест значения по умолчанию для is_active"""
        user = User(
            first_name="Тест",
            last_name="Тестов",
            email="default@example.com",
            hashed_password="hash"
        )
        
        assert user.is_active is True
    
    def test_user_string_length_constraints(self, db_session):
        """Тест ограничений длины строковых полей"""
        # Тест с корректной длиной
        user = User(
            first_name="А" * 50,  # Максимальная длина
            last_name="Б" * 50,   # Максимальная длина
            email="test@example.com",
            hashed_password="hash"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.first_name == "А" * 50
        assert user.last_name == "Б" * 50
        
        db_session.delete(user)
        db_session.commit()