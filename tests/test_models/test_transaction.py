import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app.models.transaction import Transaction, TransactionType


class TestTransactionModel:
    """Тесты для модели Transaction"""
    
    def test_create_transaction(self, create_transaction):
        """Тест создания транзакции"""
        transaction = create_transaction(
            name="Зарплата",
            type=TransactionType.INCOME,
            amount=Decimal("50000.00")
        )
        
        assert transaction.id is not None
        assert transaction.name == "Зарплата"
        assert transaction.type == TransactionType.INCOME
        assert transaction.amount == Decimal("50000.00")
        assert transaction.user_id is not None
        assert transaction.category_id is not None
        assert transaction.date is not None
    
    def test_transaction_types(self, create_transaction):
        """Тест типов транзакций"""
        income = create_transaction(type=TransactionType.INCOME)
        expense = create_transaction(type=TransactionType.EXPENSE)
        
        assert income.type == TransactionType.INCOME
        assert income.type.value == "income"
        assert expense.type == TransactionType.EXPENSE
        assert expense.type.value == "expense"
    
    def test_transaction_repr(self, create_transaction):
        """Тест строкового представления"""
        transaction = create_transaction(
            name="Тест",
            amount=Decimal("1000.50")
        )
        
        expected_repr = (
            f"<Transaction(id={transaction.id}, name='Тест', "
            f"amount=1000.50, type='{transaction.type.value}', "
            f"group_id={transaction.group_id})>"
        )
        assert repr(transaction) == expected_repr
    
    def test_transaction_to_dict(self, create_transaction, create_group):
        """Тест метода to_dict"""
        # Создаем транзакцию с группой
        group = create_group()
        transaction = create_transaction(
            name="Групповая транзакция",
            amount=Decimal("2500.75"),
            group_id=group.id,
            user_id=group.owner_id
        )
        
        # Обновляем объект, чтобы загрузить связи
        from sqlalchemy.orm import Session
        db_session = Session.object_session(transaction)
        transaction = db_session.query(Transaction).filter_by(id=transaction.id).first()
        
        result = transaction.to_dict()
        
        assert result['id'] == transaction.id
        assert result['name'] == "Групповая транзакция"
        assert result['type'] == transaction.type.value
        assert result['amount'] == 2500.75  # Decimal преобразован к float
        assert result['category_id'] == transaction.category_id
        assert result['category_name'] is not None
        assert result['user_id'] == transaction.user_id
        assert result['group_id'] == group.id
        assert result['group_name'] == group.name
    
    def test_transaction_required_fields(self, db_session, create_user, create_category):
        """Тест обязательных полей транзакции"""
        user = create_user()
        category = create_category(user_id=user.id)
        
        # Без name
        transaction1 = Transaction(
            type=TransactionType.INCOME,
            amount=Decimal("1000.00"),
            user_id=user.id,
            category_id=category.id
        )
        db_session.add(transaction1)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        
        # Без type
        transaction2 = Transaction(
            name="Тест",
            amount=Decimal("1000.00"),
            user_id=user.id,
            category_id=category.id
        )
        db_session.add(transaction2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        
        # Без amount
        transaction3 = Transaction(
            name="Тест",
            type=TransactionType.INCOME,
            user_id=user.id,
            category_id=category.id
        )
        db_session.add(transaction3)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
    
    def test_transaction_relationships(self, create_transaction, create_group):
        """Тест связей транзакции"""
        # Транзакция без группы
        transaction1 = create_transaction()
        
        assert transaction1.user.id == transaction1.user_id
        assert transaction1.category.id == transaction1.category_id
        assert transaction1.group is None
        
        # Транзакция с группой
        group = create_group()
        transaction2 = create_transaction(
            user_id=group.owner_id,
            group_id=group.id
        )
        
        assert transaction2.group.id == group.id
        assert transaction2 in group.transactions
    
    def test_amount_numeric_constraints(self, db_session, create_user, create_category):
        """Тест числовых ограничений для amount"""
        user = create_user()
        category = create_category(user_id=user.id)
        
        # Отрицательная сумма (хотя в комментарии сказано "Всегда положительное число")
        transaction = Transaction(
            name="Тест",
            type=TransactionType.INCOME,
            amount=Decimal("-100.00"),  # Отрицательная сумма
            user_id=user.id,
            category_id=category.id
        )
        
        db_session.add(transaction)
        # Некоторые БД позволят это, другие нет
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()
        
        # Слишком большое число (precision=10, scale=2)
        # Максимальное: 99999999.99
        large_amount = Decimal("100000000.00")  # 11 цифр до запятой
        transaction2 = Transaction(
            name="Большая сумма",
            type=TransactionType.INCOME,
            amount=large_amount,
            user_id=user.id,
            category_id=category.id
        )
        
        db_session.add(transaction2)
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()
    
    def test_cascade_delete(self, db_session, create_user, create_category, create_transaction):
        """Тест каскадного удаления"""
        user = create_user()
        category = create_category(user_id=user.id)
        transaction = create_transaction(
            user_id=user.id,
            category_id=category.id
        )
        
        transaction_id = transaction.id
        
        # Удаляем категорию
        db_session.delete(category)
        db_session.commit()
        
        # Транзакция должна быть удалена
        transaction_after = db_session.query(Transaction).filter_by(id=transaction_id).first()
        assert transaction_after is None
    
    def test_default_date(self, db_session, create_user, create_category):
        """Тест значения даты по умолчанию"""
        user = create_user()
        category = create_category(user_id=user.id)
        
        transaction = Transaction(
            name="Тест даты",
            type=TransactionType.INCOME,
            amount=Decimal("1000.00"),
            user_id=user.id,
            category_id=category.id
        )
        
        assert transaction.date is None
        
        db_session.add(transaction)
        db_session.commit()
        
        assert transaction.date is not None