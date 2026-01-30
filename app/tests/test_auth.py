"""
Tests para autenticación y seguridad JWT.
"""
import pytest
from sqlalchemy.orm import Session

from models.user import User
from services.auth_service import hash_password


@pytest.fixture
def admin_user(db: Session) -> dict:
    """Fixture para crear usuario admin de prueba."""
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("adminpass123"),
        is_admin=True,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "password": "adminpass123",
        "is_admin": True
    }


@pytest.fixture
def regular_user(db: Session) -> dict:
    """Fixture para crear usuario regular de prueba."""
    user = User(
        email="user@test.com",
        hashed_password=hash_password("userpass123"),
        is_admin=False,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "password": "userpass123",
        "is_admin": False
    }


def test_register_user(client):
    """Test de registro de nuevo usuario."""
    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepass123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["is_admin"] is False


def test_register_duplicate_email(client):
    """Test de registro con email duplicado."""
    email = "duplicate@example.com"
    password = "pass123"
    
    # Primer registro
    response1 = client.post(
        "/auth/register",
        json={"email": email, "password": password}
    )
    assert response1.status_code == 201
    
    # Intentar registrar con mismo email
    response2 = client.post(
        "/auth/register",
        json={"email": email, "password": "differentpass"}
    )
    assert response2.status_code == 409
    assert "already registered" in response2.json()["detail"]


def test_login_success(client, regular_user):
    """Test de login exitoso."""
    response = client.post(
        "/auth/login",
        json={
            "email": regular_user["email"],
            "password": regular_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == regular_user["email"]


def test_login_invalid_password(client, regular_user):
    """Test de login con contraseña incorrecta."""
    response = client.post(
        "/auth/login",
        json={
            "email": regular_user["email"],
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Test de login con usuario que no existe."""
    response = client.post(
        "/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "anypass"
        }
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_get_current_user(client, regular_user):
    """Test de obtener usuario actual con token."""
    # Hacer login para obtener token
    login_response = client.post(
        "/auth/login",
        json={
            "email": regular_user["email"],
            "password": regular_user["password"]
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Obtener usuario actual
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == regular_user["email"]
    assert data["is_admin"] is False


def test_get_current_user_invalid_token(client):
    """Test de acceso con token inválido."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token-xyz"}
    )
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


def test_get_current_user_no_auth(unauthenticated_client):
    """Test de acceso sin autenticación."""
    response = unauthenticated_client.get("/auth/me")
    assert response.status_code == 403


def test_admin_user_login(client, admin_user):
    """Test de login de usuario admin."""
    response = client.post(
        "/auth/login",
        json={
            "email": admin_user["email"],
            "password": admin_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["is_admin"] is True


def test_admin_user_attributes(admin_user):
    """Test de atributos de usuario admin."""
    assert admin_user["is_admin"] is True
    assert admin_user["email"] == "admin@test.com"
