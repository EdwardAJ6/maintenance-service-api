"""
Database connection and session management module.
Implements DBManager class with CRUD operations and proper session handling.
"""

import os
from pathlib import Path
from typing import Generator, TypeVar, Generic, Type, Optional, List, Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.exc import IntegrityError

from config import get_settings

settings = get_settings()

# Create engine with SQLite
# For SQLite, we need check_same_thread=False for FastAPI's async nature
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Type variable for generic model operations
T = TypeVar("T", bound=Base)


class DBManager(Generic[T]):
    """
    Generic Database Manager class with CRUD operations.
    
    Provides a reusable interface for database operations with proper
    session management using try-except-finally blocks.
    
    Usage:
        manager = DBManager(Item)
        item = manager.create(db, name="Test", sku="TST-001", price=10.0, stock=100)
        items = manager.list(db, skip=0, limit=10)
        item = manager.get(db, id=1)
        item = manager.update(db, id=1, stock=50)
        manager.delete(db, id=1)
    """
    
    def __init__(self, model: Type[T]):
        """
        Initialize DBManager with a model class.
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
    
    def create(self, db: Session, **kwargs: Any) -> T:
        """
        Create a new record in the database.
        
        Args:
            db: Database session
            **kwargs: Model field values
            
        Returns:
            Created model instance
            
        Raises:
            IntegrityError: If unique constraint is violated
        """
        db_obj = self.model(**kwargs)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise e
        except Exception as e:
            db.rollback()
            raise e
    
    def get(self, db: Session, id: int) -> Optional[T]:
        """
        Retrieve a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Model instance or None if not found
        """
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            db.rollback()
            raise e
    
    def get_by_field(self, db: Session, field_name: str, value: Any) -> Optional[T]:
        """
        Retrieve a record by a specific field value.
        
        Args:
            db: Database session
            field_name: Name of the field to filter by
            value: Value to match
            
        Returns:
            Model instance or None if not found
        """
        try:
            field = getattr(self.model, field_name)
            return db.query(self.model).filter(field == value).first()
        except Exception as e:
            db.rollback()
            raise e
    
    def list(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        desc: bool = False
    ) -> List[T]:
        """
        Retrieve a list of records with pagination and optional filtering.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional dictionary of field:value pairs to filter by
            order_by: Optional field name to order by
            desc: If True, order descending
            
        Returns:
            List of model instances
        """
        try:
            query = db.query(self.model)
            
            # Apply filters
            if filters is not None:
                for field_name, value in filters.items():
                    if value is not None:
                        field = getattr(self.model, field_name, None)
                        if field is not None:
                            query = query.filter(field == value)
            
            # Apply ordering
            if order_by is not None:
                order_field = getattr(self.model, order_by, None)
                if order_field is not None:
                    if desc:
                        query = query.order_by(order_field.desc())
                    else:
                        query = query.order_by(order_field)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            db.rollback()
            raise e
    
    def update(self, db: Session, id: int, **kwargs: Any) -> Optional[T]:
        """
        Update a record by ID with partial data.
        
        Args:
            db: Database session
            id: Record ID
            **kwargs: Fields to update (only non-None values are applied)
            
        Returns:
            Updated model instance or None if not found
        """
        try:
            db_obj = db.query(self.model).filter(self.model.id == id).first()
            
            if db_obj is None:
                return None
            
            # Update only provided fields
            for field, value in kwargs.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise e
    
    def delete(self, db: Session, id: int) -> bool:
        """
        Delete a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            db_obj = db.query(self.model).filter(self.model.id == id).first()
            
            if db_obj is None:
                return False
            
            db.delete(db_obj)
            db.commit()
            return True
        except IntegrityError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise e
    
    def exists(self, db: Session, id: int) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            True if exists, False otherwise
        """
        return self.get(db, id) is not None


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Implements proper session management with try-except-finally
    to guarantee connection closure.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # Rollback on any exception
        db.rollback()
        raise e
    finally:
        # Always close the session
        db.close()


def database_exists() -> bool:
    """
    Check if the database file exists (for SQLite).
    
    Returns:
        True if database exists or if not using SQLite
    """
    if "sqlite" in settings.database_url:
        # Extract the database file path from the URL
        # Format: sqlite:///./path/to/db.db or sqlite:///path/to/db.db
        db_path = settings.database_url.replace("sqlite:///", "")
        if db_path.startswith("./"):
            db_path = db_path[2:]
        return Path(db_path).exists()
    # For other databases, assume it exists (connection will fail if not)
    return True


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Should be called on application startup.
    """
    # Import all models to ensure they are registered with Base
    from models import item, order, category, user  # noqa: F401
    
    Base.metadata.create_all(bind=engine)
