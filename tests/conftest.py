import pytest
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.models.group import Group


# Фикстура для движка базы данных (SQLite в памяти)
@pytest.fixture(scope="session")
def engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Установите True для отладки SQL-запросов
    )


# Фикстура для создания таблиц
@pytest.fixture(scope="session", autouse=True)
def create_tables(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# Фикстура для сессии базы данных
@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


# Фикстуры для создания тестовых объектов
@pytest.fixture
def create_user(db_session: Session):
    def _create_user(
        first_name="Тест",
        last_name="Тестов",
        email=None,
        hashed_password="hashed_password_123",
        is_active=True
    ):
        if email is None:
            timestamp = datetime.now().timestamp()
            email = f"test_{timestamp}@example.com"
        
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            hashed_password=hashed_password,
            is_active=is_active
        )
        
        db_session.add(user)
        db_session.commit()
        return user
    
    return _create_user


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
        return category
    
    return _create_category


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
        group_id=None
    ):
        if user_id is None:
            user = create_user(db_session)()
            user_id = user.id
        
        if category_id is None:
            category = create_category(db_session)(user_id=user_id)
            category_id = category.id
        
        transaction = Transaction(
            name=name,
            type=type,
            amount=amount,
            user_id=user_id,
            category_id=category_id,
            group_id=group_id
        )
        
        db_session.add(transaction)
        db_session.commit()
        return transaction
    
    return _create_transaction