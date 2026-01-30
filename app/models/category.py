"""
Category model for item categorization.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base

if TYPE_CHECKING:
    from models.item import Item


class Category(Base):
    """
    Category model for grouping items/spare parts.
    
    Attributes:
        id: Primary key
        name: Category name (unique)
        description: Optional description
        created_at: Timestamp of creation
        items: Relationship to associated items
    """
    
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationship
    items: Mapped[List["Item"]] = relationship(
        "Item",
        back_populates="category",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"
