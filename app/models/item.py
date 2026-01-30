"""
Item (spare parts) model with B-Tree index on SKU column.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, DateTime, Numeric, Integer, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base

if TYPE_CHECKING:
    from models.category import Category
    from models.order import OrderItem


class Item(Base):
    """
    Item model representing spare parts/inventory items.
    
    Attributes:
        id: Primary key
        name: Item name
        sku: Stock Keeping Unit (indexed with B-Tree for optimized searches)
        price: Item price
        stock: Current stock quantity
        category_id: Foreign key to category
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "items"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="items",
        lazy="joined"  # Eager loading for LEFT JOIN
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="item",
        lazy="selectin"
    )
    
    # B-Tree index on SKU column for optimized searches
    __table_args__ = (
        Index(
            "ix_items_sku_btree",
            "sku",
            postgresql_using="btree"  # Explicit B-Tree (default for most DBs)
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Item(id={self.id}, sku='{self.sku}', name='{self.name}')>"
