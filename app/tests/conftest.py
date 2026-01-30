"""
Test configuration and fixtures.
"""

import os
import pytest
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment variables before importing app
os.environ["DEBUG"] = "True"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

# Use DATABASE_URL from environment (set by GitHub Actions), fallback to SQLite for local dev
TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./test.db"
)

from database.connection import Base

# Import all models to ensure tables are registered
from models.user import User
from models.category import Category
from models.item import Item
from models.order import Order, OrderItem, OrderStatus


# Test database setup
if "sqlite" in TEST_DATABASE_URL:
    # SQLite: use in-memory database and configure for testing
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL or other database
    engine = create_engine(TEST_DATABASE_URL, echo=False)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def authenticated_client(db: Session):
    """Create a test client with authentication and database override."""
    from fastapi.testclient import TestClient
    from main import app
    from database.connection import get_db
    from models.user import User
    from services.auth_service import hash_password, create_access_token, set_secret_key
    
    # Set JWT secret for tests
    set_secret_key("test-secret-key-for-testing-only")
    
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    test_client = TestClient(app)
    
    # Create test user
    test_user = User(
        email="testuser@test.com",
        hashed_password=hash_password("testpass123"),
        is_admin=False,
        is_active=True
    )
    db.add(test_user)
    db.commit()
    
    # Create and attach token
    token = create_access_token(
        data={
            "sub": test_user.email,
            "user_id": test_user.id,
            "is_admin": test_user.is_admin,
        }
    )
    test_client.token = token
    test_client.headers = {"Authorization": f"Bearer {token}"}
    
    yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(authenticated_client):
    """Alias para backward compatibility - usa authenticated_client."""
    return authenticated_client


@pytest.fixture(scope="function")
def unauthenticated_client(db: Session):
    """Create a test client WITHOUT authentication for testing auth endpoint behavior."""
    from fastapi.testclient import TestClient
    from main import app
    from database.connection import get_db
    
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client WITHOUT token
    test_client = TestClient(app)
    
    yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_category() -> dict:
    """Sample category data."""
    return {
        "name": "Electrónica",
        "description": "Componentes electrónicos"
    }


@pytest.fixture
def sample_item() -> dict:
    """Sample item data."""
    return {
        "name": "Filtro de Aceite",
        "sku": "FIL-ACE-001",
        "price": 25.99,
        "stock": 100
    }


@pytest.fixture
def sample_order() -> dict:
    """Sample order data."""
    return {
        "request_id": "ORD-TEST-001",
        "technical_report": "Mantenimiento preventivo del motor",
        "items": [
            {"item_id": 1, "quantity": 2}
        ]
    }
