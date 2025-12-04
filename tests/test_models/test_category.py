import pytest
from sqlalchemy.exc import IntegrityError
from app.models.category import Category


class TestCategoryModel:
    """Тесты для модели Category"""
    
    def test_create_category(self, create_category):
        """Тест создания категории"""
        category = create_category(
            name="Продукты",
            description="Покупка продуктов питания"
        )
        
        assert category.id is not None
        assert category.name == "Продукты"
        assert category.description == "Покупка продуктов питания"
        assert category.user_id is not None
    
    def test_category_repr(self, create_category):
        """Тест строкового представления"""
        category = create_category(name="Тестовая категория")
        
        expected_repr = f"<Category(id={category.id}, name='Тестовая категория', user_id={category.user_id})>"
        assert repr(category) == expected_repr
    
    def test_category_required_fields(self, db_session, create_user):
        """Тест обязательных полей"""
        user = create_user()
        
        # Категория без name
        category1 = Category(
            description="Без имени",
            user_id=user.id
        )
        db_session.add(category1)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        
        # Категория без user_id
        category2 = Category(
            name="Категория",
            description="Без пользователя"
        )
        db_session.add(category2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
    
    def test_category_user_relationship(self, create_category, create_user):
        """Тест связи с пользователем"""
        user = create_user()
        category = create_category(user_id=user.id)
        
        # Проверяем прямую связь
        assert category.user.id == user.id
        assert category.user.email == user.email
        
        # Проверяем обратную связь
        assert len(user.categories) == 1
        assert user.categories[0].id == category.id
    
    def test_category_transactions_relationship(self, db_session, create_category, create_transaction):
        """Тест связи с транзакциями"""
        category = create_category()
        
        # Создаем транзакции для категории
        transaction1 = create_transaction(
            name="Транзакция 1",
            category_id=category.id,
            user_id=category.user_id
        )
        
        transaction2 = create_transaction(
            name="Транзакция 2",
            category_id=category.id,
            user_id=category.user_id
        )
        
        # Проверяем связь
        assert len(category.transactions) == 2
        assert {t.id for t in category.transactions} == {transaction1.id, transaction2.id}
        
        # Проверяем обратную связь
        assert transaction1.category.id == category.id
        assert transaction2.category.id == category.id
    
    def test_cascade_delete_user(self, db_session, create_user, create_category):
        """Тест каскадного удаления при удалении пользователя"""
        user = create_user()
        category = create_category(user_id=user.id)
        
        # Сохраняем ID категории
        category_id = category.id
        
        # Удаляем пользователя
        db_session.delete(user)
        db_session.commit()
        
        # Проверяем, что категория тоже удалена
        category_after = db_session.query(Category).filter_by(id=category_id).first()
        assert category_after is None
    
    def test_category_name_not_unique_globally(self, db_session, create_user):
        """Тест, что название категории не должно быть глобально уникальным"""
        user1 = create_user(email="user1@example.com")
        user2 = create_user(email="user2@example.com")
        
        # Два пользователя могут иметь категории с одинаковым именем
        category1 = Category(
            name="Одинаковое имя",
            description="Категория первого пользователя",
            user_id=user1.id
        )
        
        category2 = Category(
            name="Одинаковое имя",
            description="Категория второго пользователя",
            user_id=user2.id
        )
        
        db_session.add_all([category1, category2])
        db_session.commit()
        
        assert category1.name == category2.name
        assert category1.id != category2.id
    
    def test_string_length_constraint(self, db_session, create_user):
        """Тест ограничения длины названия категории"""
        user = create_user()
        
        # Название длиной 100 символов (максимум)
        long_name = "К" * 100
        category1 = Category(
            name=long_name,
            user_id=user.id
        )
        
        db_session.add(category1)
        db_session.commit()
        
        assert category1.name == long_name
        
        # Очистка
        db_session.delete(category1)
        db_session.commit()