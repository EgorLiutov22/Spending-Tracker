import pytest
from pydantic import ValidationError
from datetime import date
from uuid import UUID

# Импорты схем проекта
from app.schemas.schema_User_login import UserLogin
from app.schemas.analytic_schema import AnalyticsOverview, CategorySummary, DailySummary, ExportParams
from app.schemas.category_schema import CategoryBase, CategoryCreate, CategoryUpdate
from app.schemas.token_schema import Token, TokenData
from app.schemas.user_create import UserCreate
from app.schemas.user_schema import UserResponse


class TestUserLogin:
    """Tests for UserLogin schema - authentication validation"""
    
    def test_valid_email_login(self):
        valid_data = {"login": "user@example.com", "password": "SecurePass123"}
        user = UserLogin(**valid_data)
        assert user.login == "user@example.com"
        assert user.password == "SecurePass123"

    def test_login_with_spaces_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(login="user name", password="SecurePass123")
        assert "не должен содержать пробелы" in str(exc_info.value)

    def test_password_complexity_validation(self):
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(login="user@example.com", password="simple")
        assert "хотя бы одну цифру" in str(exc_info.value)


class TestAnalyticSchema:
    """Tests for analytics data structures"""
    
    def test_analytics_overview_creation(self):
        data = {
            "balance": 1500.50,
            "total_income": 5000.0,
            "total_expense": 3500.50,
            "period_start": date(2024, 1, 1),
            "period_end": date(2024, 1, 31)
        }
        analytics = AnalyticsOverview(**data)
        assert analytics.balance == 1500.50
        assert analytics.total_income == 5000.0

    def test_export_params_default_format(self):
        params = ExportParams()
        assert params.format == "csv"
        assert params.start_date is None


class TestCategorySchema:
    """Tests for category management schemas"""
    
    def test_category_creation_with_description(self):
        category = CategoryCreate(
            name="Food & Dining", 
            description="Groceries, restaurants, and food delivery"
        )
        assert category.name == "Food & Dining"
        assert category.description is not None

    def test_category_update_partial_data(self):
        category = CategoryUpdate(description="Updated category description")
        assert category.name is None
        assert category.description == "Updated category description"


class TestUserManagement:
    """Tests for user-related schemas"""
    
    def test_user_creation_validation(self):
        user_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "password": "secure123"
        }
        user = UserCreate(**user_data)
        assert user.first_name == "John"
        assert user.email == "john.doe@example.com"

    def test_user_response_serialization(self):
        user_data = {
            "uid": "12345678-1234-1234-1234-123456789abc",
            "email": "user@example.com",
            "status": True,
            "first_name": "Alice",
            "last_name": "Smith"
        }
        user = UserResponse(**user_data)
        assert isinstance(user.uid, UUID)
        assert user.status is True


class TestTokenSchema:
    """Tests for authentication token schemas"""
    
    def test_token_creation(self):
        token = Token(access_token="eyJhbGciOiJIUzI1NiIs", token_type="bearer")
        assert token.access_token == "eyJhbGciOiJIUzI1NiIs"
        assert token.token_type == "bearer"
