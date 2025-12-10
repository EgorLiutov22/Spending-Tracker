"""
Модульные тесты для сервиса транзакций
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.transaction import TransactionType
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.transaction import TransactionService


class TestTransactionServiceUnit:
    """Модульные тесты сервиса транзакций"""
    
    def test_create_transaction(
        self, 
        transaction_service: TransactionService,
        auth_user,
        test_categories
    ):
        """Тест создания транзакции"""
        transaction_data = TransactionCreate(
            name="Тестовая транзакция сервис",
            type=TransactionType.INCOME,
            category_id=test_categories["Зарплата"].id,
            amount=12345.67,
        )
        
        transaction = transaction_service.create_transaction(
            transaction_data, 
            auth_user.id
        )
        
        assert transaction is not None
        assert transaction.name == transaction_data.name
        assert transaction.type == transaction_data.type
        assert transaction.amount == Decimal(str(transaction_data.amount))
        assert transaction.user_id == auth_user.id
        assert transaction.category_id == transaction_data.category_id
    
    def test_get_transaction_by_id(
        self, 
        transaction_service: TransactionService,
        auth_user,
        test_transactions
    ):
        """Тест получения транзакции по ID"""
        transaction = test_transactions["Зарплата за январь"]
        
        retrieved = transaction_service.get_transaction(
            transaction.id, 
            auth_user.id
        )
        
        assert retrieved is not None
        assert retrieved.id == transaction.id
        assert retrieved.name == transaction.name
        assert retrieved.user_id == auth_user.id
    
    def test_get_transaction_not_found(
        self, 
        transaction_service: TransactionService,
        auth_user
    ):
        """Тест получения несуществующей транзакции"""
        transaction = transaction_service.get_transaction(999999, auth_user.id)
        assert transaction is None
    
    def test_get_user_transactions(
        self, 
        transaction_service: TransactionService,
        auth_user,
        test_transactions
    ):
        """Тест получения транзакций пользователя"""
        transactions, total = transaction_service.get_user_transactions(
            user_id=auth_user.id,
            skip=0,
            limit=10
        )
        
        assert total == len(test_transactions)
        assert len(transactions) == len(test_transactions)
        
        # Все транзакции должны принадлежать пользователю
        for transaction in transactions:
            assert transaction.user_id == auth_user.id
    
    def test_get_user_transactions_with_filters(
        self, 
        transaction_service: TransactionService,
        auth_user,
        test_transactions,
        test_categories
    ):
        """Тест получения транзакций с фильтрами"""
        # Фильтр по типу
        transactions, total = transaction_service.get_user_transactions(
            user_id=auth_user.id,
            type=TransactionType.EXPENSE
        )
        
        # В тестовых данных 4 расхода
        assert total == 4
        for transaction in transactions:
            assert transaction.type == TransactionType.EXPENSE
        
        # Фильтр по категории
        category_id = test_categories["Продукты"].id
        transactions, total = transaction_service.get_user_transactions(
            user_id=auth_user.id,
            category_id=category_id
        )
        
        assert total == 1
        for transaction in transactions:
            assert transaction.category_id == category_id
    
    def test_update_transaction(
        self, 
        transaction_service: TransactionService,
        auth_user,
        test_transactions,
        test_categories
    ):
        """Тест обновления транзакции"""
        transaction = test_transactions["Покупка продуктов"]
        
        update_data = TransactionUpdate(
            name="Обновленная покупка",
            amount=5500.00,
            category_id=test_categories["Транспорт"].id
        )
        
        updated = transaction_service.update_transaction(
            transaction_id=transaction.id,
            user_id=auth_user.id,
            update_data=update_data
        )
        
        assert updated is not None
        assert updated.name == update_data.name
        assert updated.amount == Decimal(str(update_data.amount))
        assert updated.category_id == update_data.category_id
    
    def test_update_nonexistent_transaction(
        self, 
        transaction_service: TransactionService,
        auth_user
    ):
        """Тест обновления несуществующей транзакции"""
        update_data = TransactionUpdate(name="Новое название")
        
        updated = transaction_service.update_transaction(
            transaction_id=999999,
            user_id=auth_user.id,
            update_data=update_data
        )
        
        assert updated is None
    
    def test_delete_transaction(
        self, 
        transaction_service: TransactionService,
        auth_user,
        test_transactions
    ):
        """Тест удаления транзакции"""
        transaction = test_transactions["Поход в кино"]
        
        success = transaction_service.delete_transaction(
            transaction.id, 
            auth_user.id
        )
        
        assert success is True
        
        # Проверяем, что транзакция удалена
        deleted = transaction_service.get_transaction(transaction.id, auth_user.id)
        assert deleted is None
    
    def test_delete_nonexistent_transaction(
        self, 
        transaction_service: TransactionService,
        auth_user
    ):
        """Тест удаления несуществующей транзакции"""
        success = transaction_service.delete_transaction(999999, auth_user.id)
        assert success is False
    
    def test_financial_summary(
        self, 
        transaction_service: TransactionService,
        auth_user
    ):
        """Тест финансовой сводки"""
        summary = transaction_service.get_financial_summary(auth_user.id)
        
        assert "total_income" in summary
        assert "total_expense" in summary
        assert "balance" in summary
        assert "transaction_count" in summary
        
        # Проверяем правильность расчетов
        assert summary["balance"] == summary["total_income"] - summary["total_expense"]
    
    def test_category_summary(
        self, 
        transaction_service: TransactionService,
        auth_user
    ):
        """Тест сводки по категориям"""
        summary = transaction_service.get_category_summary(auth_user.id)
        
        assert isinstance(summary, list)
        
        if summary:
            for item in summary:
                assert "category_id" in item
                assert "category_name" in item
                assert "total_amount" in item
                assert "transaction_count" in item
    
    def test_recent_transactions(
        self, 
        transaction_service: TransactionService,
        auth_user
    ):
        """Тест получения последних транзакций"""
        recent = transaction_service.get_recent_transactions(auth_user.id, limit=3)
        
        assert isinstance(recent, list)
        assert len(recent) <= 3
        
        # Проверяем сортировку по дате (новые сначала)
        if len(recent) > 1:
            dates = [t.date for t in recent]
            assert dates == sorted(dates, reverse=True)
    
    def test_search_transactions(
        self, 
        transaction_service: TransactionService,
        auth_user
    ):
        """Тест поиска транзакций"""
        results = transaction_service.search_transactions(
            user_id=auth_user.id,
            search_term="зарплата",
            limit=10
        )
        
        assert isinstance(results, list)
        
        if results:
            for transaction in results:
                assert "зарплата" in transaction.name.lower()