"""
Тесты API эндпоинтов для транзакций
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from fastapi import status

from app.models.enums import TransactionType


class TestTransactionEndpoints:
    """Тесты эндпоинтов транзакций"""
    
    def test_create_transaction_success(
        self, 
        test_client, 
        auth_headers, 
        test_categories
    ):
        """Тест успешного создания транзакции через API"""
        transaction_data = {
            "name": "Тестовая транзакция API",
            "type": TransactionType.INCOME.value,
            "category_id": test_categories["Зарплата"].id,
            "amount": 7500.50,
            "date": datetime.now().isoformat(),
        }
        
        response = test_client.post(
            "/api/transactions/",
            json=transaction_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["name"] == transaction_data["name"]
        assert data["type"] == transaction_data["type"]
        assert data["category_id"] == transaction_data["category_id"]
        assert data["amount"] == transaction_data["amount"]
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data
    
    def test_create_transaction_without_auth(self, test_client):
        """Тест создания транзакции без авторизации"""
        transaction_data = {
            "name": "Тестовая транзакция",
            "type": TransactionType.INCOME.value,
            "category_id": 1,
            "amount": 1000.00,
        }
        
        response = test_client.post(
            "/api/transactions/",
            json=transaction_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_transactions_list(
        self, 
        test_client, 
        auth_headers, 
        test_transactions
    ):
        """Тест получения списка транзакций"""
        response = test_client.get(
            "/api/transactions/",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "transactions" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        
        assert data["total"] == len(test_transactions)
        assert len(data["transactions"]) == len(test_transactions)
    
    def test_get_transactions_with_pagination(
        self, 
        test_client, 
        auth_headers, 
        test_transactions
    ):
        """Тест пагинации в списке транзакций"""
        response = test_client.get(
            "/api/transactions/?skip=1&limit=2",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["transactions"]) == 2
        assert data["skip"] == 1
        assert data["limit"] == 2
        assert data["total"] == len(test_transactions)
    
    def test_get_transactions_filter_by_type(
        self, 
        test_client, 
        auth_headers, 
        test_transactions
    ):
        """Тест фильтрации транзакций по типу"""
        response = test_client.get(
            f"/api/transactions/?type={TransactionType.INCOME.value}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # В тестовых данных только 1 доход
        assert data["total"] == 1
        for transaction in data["transactions"]:
            assert transaction["type"] == TransactionType.INCOME.value
    
    def test_get_transactions_filter_by_category(
        self, 
        test_client, 
        auth_headers, 
        test_transactions,
        test_categories
    ):
        """Тест фильтрации транзакций по категории"""
        category_id = test_categories["Продукты"].id
        
        response = test_client.get(
            f"/api/transactions/?category_id={category_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # В тестовых данных 1 транзакция в категории "Продукты"
        assert data["total"] == 1
        for transaction in data["transactions"]:
            assert transaction["category_id"] == category_id
    
    def test_get_transactions_filter_by_date_range(
        self, 
        test_client, 
        auth_headers,
        db_session,
        auth_user,
        test_categories
    ):
        """Тест фильтрации по диапазону дат"""
        # Создаем транзакции с разными датами
        today = datetime.now()
        
        from app.models.transaction import Transaction
        
        # Транзакция 5 дней назад
        transaction1 = Transaction(
            name="Старая транзакция",
            type=TransactionType.INCOME,
            amount=Decimal("1000.00"),
            user_id=auth_user.id,
            category_id=test_categories["Зарплата"].id,
            date=today - timedelta(days=5)
        )
        
        # Транзакция сегодня
        transaction2 = Transaction(
            name="Сегодняшняя транзакция",
            type=TransactionType.EXPENSE,
            amount=Decimal("500.00"),
            user_id=auth_user.id,
            category_id=test_categories["Продукты"].id,
            date=today
        )
        
        db_session.add_all([transaction1, transaction2])
        db_session.commit()
        
        # Фильтр за последние 3 дня
        start_date = (date.today() - timedelta(days=3)).isoformat()
        
        response = test_client.get(
            f"/api/transactions/?start_date={start_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Должна быть только сегодняшняя транзакция
        assert data["total"] >= 1
        assert any(t["name"] == "Сегодняшняя транзакция" for t in data["transactions"])
    
    def test_get_single_transaction(
        self, 
        test_client, 
        auth_headers, 
        test_transactions
    ):
        """Тест получения одной транзакции"""
        transaction = test_transactions["Зарплата за январь"]
        
        response = test_client.get(
            f"/api/transactions/{transaction.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == transaction.id
        assert data["name"] == transaction.name
        assert data["amount"] == float(transaction.amount)
        assert "category" in data
    
    def test_get_nonexistent_transaction(
        self, 
        test_client, 
        auth_headers
    ):
        """Тест получения несуществующей транзакции"""
        response = test_client.get(
            "/api/transactions/999999",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_transaction(
        self, 
        test_client, 
        auth_headers, 
        test_transactions,
        test_categories
    ):
        """Тест обновления транзакции"""
        transaction = test_transactions["Покупка продуктов"]
        
        update_data = {
            "name": "Обновленная покупка продуктов",
            "amount": 5500.00,
            "category_id": test_categories["Транспорт"].id,
        }
        
        response = test_client.put(
            f"/api/transactions/{transaction.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["name"] == update_data["name"]
        assert data["amount"] == update_data["amount"]
        assert data["category_id"] == update_data["category_id"]
    
    def test_update_transaction_partial(
        self, 
        test_client, 
        auth_headers, 
        test_transactions
    ):
        """Тест частичного обновления транзакции"""
        transaction = test_transactions["Такси на работу"]
        
        # Обновляем только название
        update_data = {"name": "Обновленное такси"}
        
        response = test_client.put(
            f"/api/transactions/{transaction.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["name"] == update_data["name"]
        # Остальные поля должны остаться без изменений
        assert data["amount"] == float(transaction.amount)
        assert data["category_id"] == transaction.category_id
    
    def test_delete_transaction(
        self, 
        test_client, 
        auth_headers, 
        test_transactions
    ):
        """Тест удаления транзакции"""
        transaction = test_transactions["Поход в кино"]
        
        # Удаляем транзакцию
        response = test_client.delete(
            f"/api/transactions/{transaction.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Проверяем, что транзакция действительно удалена
        response = test_client.get(
            f"/api/transactions/{transaction.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_nonexistent_transaction(
        self, 
        test_client, 
        auth_headers
    ):
        """Тест удаления несуществующей транзакции"""
        response = test_client.delete(
            "/api/transactions/999999",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_validation_errors(
        self, 
        test_client, 
        auth_headers, 
        test_categories
    ):
        """Тест валидационных ошибок"""
        # Неправильный тип транзакции
        invalid_data = {
            "name": "Тест",
            "type": "INVALID_TYPE",  # Неправильный тип
            "category_id": test_categories["Зарплата"].id,
            "amount": 1000.00,
        }
        
        response = test_client.post(
            "/api/transactions/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Отрицательная сумма
        invalid_data["type"] = TransactionType.INCOME.value
        invalid_data["amount"] = -100.00
        
        response = test_client.post(
            "/api/transactions/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Слишком длинное название
        invalid_data["amount"] = 1000.00
        invalid_data["name"] = "A" * 101  # 101 символ
        
        response = test_client.post(
            "/api/transactions/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestTransactionAnalyticsEndpoints:
    """Тесты эндпоинтов аналитики транзакций"""
    
    def test_financial_summary(
        self, 
        test_client, 
        auth_headers, 
        test_transactions
    ):
        """Тест получения финансовой сводки"""
        response = test_client.get(
            "/api/analytics/summary",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "total_income" in data
        assert "total_expense" in data
        assert "balance" in data
        assert "transaction_count" in data
        
        # Проверяем расчеты
        assert data["total_income"] == 100000.00
        assert data["total_expense"] == 16500.00  # 5000 + 7000 + 1500 + 3000
        assert data["balance"] == data["total_income"] - data["total_expense"]
        assert data["transaction_count"] == 5
    
    def test_category_summary(
        self, 
        test_client, 
        auth_headers
    ):
        """Тест получения сводки по категориям"""
        response = test_client.get(
            "/api/analytics/by-category",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        
        # Проверяем структуру данных
        if data:  # Если есть данные
            for item in data:
                assert "category_id" in item
                assert "category_name" in item
                assert "total_amount" in item
                assert "transaction_count" in item
    
    def test_top_categories(
        self, 
        test_client, 
        auth_headers
    ):
        """Тест получения топ-категорий"""
        response = test_client.get(
            f"/api/analytics/top-categories?type={TransactionType.EXPENSE.value}&limit=3",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) <= 3
        
        # Проверяем сортировку (по убыванию суммы)
        if len(data) > 1:
            amounts = [item["total_amount"] for item in data]
            assert amounts == sorted(amounts, reverse=True)
    
    def test_recent_transactions(
        self, 
        test_client, 
        auth_headers
    ):
        """Тест получения последних транзакций"""
        response = test_client.get(
            "/api/transactions/recent?limit=3",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) <= 3
    
    def test_search_transactions(
        self, 
        test_client, 
        auth_headers, 
        test_transactions
    ):
        """Тест поиска транзакций"""
        response = test_client.get(
            "/api/transactions/search?query=зарплата",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        
        # Должна найтись хотя бы одна транзакция с "зарплата"
        if data:
            assert any("зарплата" in t["name"].lower() for t in data)