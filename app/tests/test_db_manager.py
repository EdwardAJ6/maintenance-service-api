"""
Tests for DBManager class.
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import DBManager
from models import Category, Item


class TestDBManager:
    """Test suite for DBManager class."""

    def test_create(self, db: Session):
        """Test DBManager create method."""
        manager = DBManager(Category)
        
        category = manager.create(db, name="Test Category", description="Test")
        
        assert category.id is not None
        assert category.name == "Test Category"

    def test_get(self, db: Session):
        """Test DBManager get method."""
        manager = DBManager(Category)
        created = manager.create(db, name="Test", description="Test")
        
        retrieved = manager.get(db, id=created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_not_found(self, db: Session):
        """Test DBManager get returns None for non-existent ID."""
        manager = DBManager(Category)
        
        result = manager.get(db, id=999)
        
        assert result is None

    def test_get_by_field(self, db: Session):
        """Test DBManager get_by_field method."""
        manager = DBManager(Category)
        manager.create(db, name="Unique Name", description="Test")
        
        result = manager.get_by_field(db, "name", "Unique Name")
        
        assert result is not None
        assert result.name == "Unique Name"

    def test_list(self, db: Session):
        """Test DBManager list method."""
        manager = DBManager(Category)
        manager.create(db, name="Category 1")
        manager.create(db, name="Category 2")
        manager.create(db, name="Category 3")
        
        results = manager.list(db)
        
        assert len(results) == 3

    def test_list_with_pagination(self, db: Session):
        """Test DBManager list with pagination."""
        manager = DBManager(Category)
        for i in range(10):
            manager.create(db, name=f"Category {i}")
        
        results = manager.list(db, skip=2, limit=3)
        
        assert len(results) == 3

    def test_list_with_filters(self, db: Session):
        """Test DBManager list with filters."""
        cat_manager = DBManager(Category)
        item_manager = DBManager(Item)
        
        cat = cat_manager.create(db, name="Electronics")
        item_manager.create(db, name="Item 1", sku="SKU-001", price=10, stock=5, category_id=cat.id)
        item_manager.create(db, name="Item 2", sku="SKU-002", price=20, stock=10, category_id=cat.id)
        item_manager.create(db, name="Item 3", sku="SKU-003", price=30, stock=15, category_id=None)
        
        results = item_manager.list(db, filters={"category_id": cat.id})
        
        assert len(results) == 2

    def test_update(self, db: Session):
        """Test DBManager update method."""
        manager = DBManager(Category)
        created = manager.create(db, name="Original", description="Original desc")
        
        updated = manager.update(db, id=created.id, name="Updated", description="New desc")
        
        assert updated.name == "Updated"
        assert updated.description == "New desc"

    def test_update_partial(self, db: Session):
        """Test DBManager partial update."""
        manager = DBManager(Category)
        created = manager.create(db, name="Original", description="Keep this")
        
        updated = manager.update(db, id=created.id, name="Updated")
        
        assert updated.name == "Updated"
        assert updated.description == "Keep this"  # Unchanged

    def test_update_not_found(self, db: Session):
        """Test DBManager update returns None for non-existent ID."""
        manager = DBManager(Category)
        
        result = manager.update(db, id=999, name="Updated")
        
        assert result is None

    def test_delete(self, db: Session):
        """Test DBManager delete method."""
        manager = DBManager(Category)
        created = manager.create(db, name="To Delete")
        
        result = manager.delete(db, id=created.id)
        
        assert result is True
        assert manager.get(db, id=created.id) is None

    def test_delete_not_found(self, db: Session):
        """Test DBManager delete returns False for non-existent ID."""
        manager = DBManager(Category)
        
        result = manager.delete(db, id=999)
        
        assert result is False

    def test_exists(self, db: Session):
        """Test DBManager exists method."""
        manager = DBManager(Category)
        created = manager.create(db, name="Exists")
        
        assert manager.exists(db, id=created.id) is True
        assert manager.exists(db, id=999) is False
