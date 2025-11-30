import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.user import User

# Тестовая база данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def client():
    """Фикстура для тестового клиента"""
    # Переопределяем зависимость базы данных
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def setup_database():
    """Фикстура для настройки базы данных"""
    # Создаем только таблицу users перед каждым тестом
    User.metadata.create_all(bind=engine)
    yield
    # Удаляем таблицы после каждого теста
    Base.metadata.drop_all(bind=engine)


def test_register_user_success(client, setup_database):
    """Тест успешной регистрации пользователя"""
    user_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "password": "securepassword123"
    }

    response = client.post("/api/auth/register", json=user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["first_name"] == user_data["first_name"]
    assert data["last_name"] == user_data["last_name"]
    assert "id" in data
    assert "hashed_password" not in data
    assert data["is_active"] == True


def test_register_user_duplicate_email(client, setup_database):
    """Тест регистрации с уже существующим email"""
    user_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "password": "securepassword123"
    }

    # Первая регистрация
    client.post("/api/auth/register", json=user_data)

    # Вторая попытка регистрации с тем же email
    response = client.post("/api/auth/register", json=user_data)

    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_login_success(client, setup_database):
    """Тест успешного входа"""
    # Сначала регистрируем пользователя
    user_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "password": "securepassword123"
    }

    client.post("/api/auth/register", json=user_data)

    # Пытаемся войти
    login_data = {
        "username": "john.doe@example.com",
        "password": "securepassword123"
    }

    response = client.post("/api/auth/login", data=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, setup_database):
    """Тест входа с неправильным паролем"""
    user_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "password": "securepassword123"
    }

    client.post("/api/auth/register", json=user_data)

    login_data = {
        "username": "john.doe@example.com",
        "password": "wrongpassword"
    }

    response = client.post("/api/auth/login", data=login_data)

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_nonexistent_user(client, setup_database):
    """Тест входа с несуществующим пользователем"""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "somepassword"
    }

    response = client.post("/api/auth/login", data=login_data)

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_get_me_authenticated(client, setup_database):
    """Тест получения информации о текущем пользователе"""
    # Регистрируем и логинимся
    user_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "password": "securepassword123"
    }

    client.post("/api/auth/register", json=user_data)

    login_data = {
        "username": "john.doe@example.com",
        "password": "securepassword123"
    }

    login_response = client.post("/api/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # Получаем информацию о себе
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["first_name"] == user_data["first_name"]
    assert data["last_name"] == user_data["last_name"]


def test_get_me_unauthenticated(client, setup_database):
    """Тест получения информации без аутентификации"""
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_change_password_success(client, setup_database):
    """Тест успешной смены пароля"""
    # Регистрируем и логинимся
    user_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "password": "oldpassword123"
    }

    client.post("/api/auth/register", json=user_data)

    login_data = {
        "username": "john.doe@example.com",
        "password": "oldpassword123"
    }

    login_response = client.post("/api/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # Меняем пароль
    headers = {"Authorization": f"Bearer {token}"}
    change_password_data = {
        "current_password": "oldpassword123",
        "new_password": "newpassword456"
    }

    response = client.post("/api/auth/change-password", headers=headers, json=change_password_data)

    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"

    # Проверяем, что новый пароль работает
    new_login_data = {
        "username": "john.doe@example.com",
        "password": "newpassword456"
    }

    new_login_response = client.post("/api/auth/login", data=new_login_data)
    assert new_login_response.status_code == 200


def test_change_password_wrong_current_password(client, setup_database):
    """Тест смены пароля с неправильным текущим паролем"""
    user_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "password": "oldpassword123"
    }

    client.post("/api/auth/register", json=user_data)

    login_data = {
        "username": "john.doe@example.com",
        "password": "oldpassword123"
    }

    login_response = client.post("/api/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    change_password_data = {
        "current_password": "wrongpassword",
        "new_password": "newpassword456"
    }

    response = client.post("/api/auth/change-password", headers=headers, json=change_password_data)

    assert response.status_code == 400
    assert "Current password is incorrect" in response.json()["detail"]


def test_logout(client, setup_database):
    """Тест выхода из системы"""
    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"


def test_user_model_repr(setup_database):
    """Тест строкового представления модели User"""
    with TestingSessionLocal() as db:
        user = User(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            hashed_password="hashed_password"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert repr(user) == f"<User(id={user.id}, email='{user.email}')>"


def test_user_get_full_name(setup_database):
    """Тест метода получения полного имени пользователя"""
    with TestingSessionLocal() as db:
        user = User(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            hashed_password="hashed_password"
        )

        assert user.get_full_name() == "John Doe"