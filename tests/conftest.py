import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.models.group import Group
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService


# Фикстура для движка базы данных (SQLite в памяти)
@pytest.fixture(scope="session")
def engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )


# Фикстура для создания таблиц
@pytest.fixture(scope="session", autouse=True)
def create_tables(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# Фикстура для фабрики сессий
@pytest.fixture(scope="session")
def session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Фикстура для сессии базы данных
@pytest.fixture
def db_session(session_factory) -> Generator[Session, None, None]:
    """Фикстура для сессии базы данных с откатом изменений после теста"""
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# Переопределяем зависимость get_db для тестов
@pytest.fixture(scope="module")
def override_get_db(session_factory):
    """Переопределение зависимости get_db для тестов"""
    def _get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()
    
    return _get_db


# Фикстура для тестового клиента
@pytest.fixture(scope="module")
def test_client(override_get_db):
    """Фикстура для тестового клиента FastAPI"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# Фикстуры для создания тестовых объектов
@pytest.fixture
def create_user(db_session: Session):
    def _create_user(
        username="testuser",
        email=None,
        password="testpassword123",
        first_name="Тест",
        last_name="Тестов",
        is_active=True
    ):
        if email is None:
            timestamp = datetime.now().timestamp()
            email = f"test_{timestamp}@example.com"
        
        # Создаем пользователя через AuthService для получения хэшированного пароля
        auth_service = AuthService()
        
        user_data = UserCreate(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        user = auth_service.create_user(db_session, user_data)
        return user
    
    return _create_user


@pytest.fixture
def auth_user(db_session: Session) -> User:
    """Фикстура для создания пользователя с авторизацией"""
    auth_service = AuthService()
    
    user_data = UserCreate(
        username="authuser",
        email="auth@example.com",
        password="authpassword123",
        first_name="Auth",
        last_name="User"
    )
    
    user = auth_service.create_user(db_session, user_data)
    return user


@pytest.fixture
def auth_headers(auth_user: User) -> Dict[str, str]:
    """Фикстура для заголовков авторизации"""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": auth_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def create_category(db_session: Session):
    def _create_category(
        name="Тестовая категория",
        description="Описание тестовой категории",
        user_id=None
    ):
        if user_id is None:
            user = create_user(db_session)()
            user_id = user.id
        
        category = Category(
            name=name,
            description=description,
            user_id=user_id
        )
        
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
        return category
    
    return _create_category


@pytest.fixture
def test_categories(db_session: Session, auth_user: User) -> Dict[str, Category]:
    """Фикстура для создания набора тестовых категорий"""
    categories_data = [
        {"name": "Зарплата", "description": "Доходы от работы", "user_id": auth_user.id},
        {"name": "Продукты", "description": "Покупка продуктов", "user_id": auth_user.id},
        {"name": "Транспорт", "description": "Транспортные расходы", "user_id": auth_user.id},
        {"name": "Развлечения", "description": "Развлекательные расходы", "user_id": auth_user.id},
        {"name": "Коммуналка", "description": "Коммунальные услуги", "user_id": auth_user.id},
    ]
    
    categories = {}
    for data in categories_data:
        category = Category(**data)
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
        categories[category.name] = category
    
    return categories


@pytest.fixture
def create_group(db_session: Session):
    def _create_group(
        name="Тестовая группа",
        description="Описание тестовой группы",
        owner_id=None
    ):
        if owner_id is None:
            owner = create_user(db_session)()
            owner_id = owner.id
        
        group = Group(
            name=name,
            description=description,
            owner_id=owner_id
        )
        
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)
        return group
    
    return _create_group


@pytest.fixture
def create_transaction(db_session: Session):
    def _create_transaction(
        name="Тестовая транзакция",
        type=TransactionType.INCOME,
        amount=Decimal("1000.00"),
        user_id=None,
        category_id=None,
        group_id=None,
        date=None
    ):
        if user_id is None:
            user = create_user(db_session)()
            user_id = user.id
        
        if category_id is None:
            category = create_category(db_session)(user_id=user_id)
            category_id = category.id
        
        if date is None:
            date = datetime.now(timezone.utc)
        
        transaction = Transaction(
            name=name,
            type=type,
            amount=amount,
            user_id=user_id,
            category_id=category_id,
            group_id=group_id,
            date=date
        )
        
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(transaction)
        return transaction
    
    return _create_transaction


@pytest.fixture
def test_transactions(db_session: Session, auth_user: User, test_categories: Dict[str, Category]) -> Dict[str, Transaction]:
    """Фикстура для создания набора тестовых транзакций"""
    transactions_data = [
        {
            "name": "Зарплата за январь",
            "type": TransactionType.INCOME,
            "amount": Decimal("100000.00"),
            "user_id": auth_user.id,
            "category_id": test_categories["Зарплата"].id,
            "date": datetime.now(timezone.utc) - timedelta(days=30)
        },
        {
            "name": "Покупка продуктов",
            "type": TransactionType.EXPENSE,
            "amount": Decimal("5000.00"),
            "user_id": auth_user.id,
            "category_id": test_categories["Продукты"].id,
            "date": datetime.now(timezone.utc) - timedelta(days=15)
        },
        {
            "name": "Оплата коммуналки",
            "type": TransactionType.EXPENSE,
            "amount": Decimal("7000.00"),
            "user_id": auth_user.id,
            "category_id": test_categories["Коммуналка"].id,
            "date": datetime.now(timezone.utc) - timedelta(days=10)
        },
        {
            "name": "Такси на работу",
            "type": TransactionType.EXPENSE,
            "amount": Decimal("1500.00"),
            "user_id": auth_user.id,
            "category_id": test_categories["Транспорт"].id,
            "date": datetime.now(timezone.utc) - timedelta(days=5)
        },
        {
            "name": "Поход в кино",
            "type": TransactionType.EXPENSE,
            "amount": Decimal("3000.00"),
            "user_id": auth_user.id,
            "category_id": test_categories["Развлечения"].id,
            "date": datetime.now(timezone.utc) - timedelta(days=2)
        },
    ]
    
    transactions = {}
    for data in transactions_data:
        transaction = Transaction(**data)
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(transaction)
        transactions[transaction.name] = transaction
    
    return transactions


@pytest.fixture
def transaction_service(db_session: Session):
    """Фикстура для сервиса транзакций"""
    from app.services.transaction import TransactionService
    return TransactionService(db_session)