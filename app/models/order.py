"""
Order and OrderItem models for maintenance orders.
Implements idempotency through unique request_id constraint.

The Order entity LINKS items (spare parts) with a TechnicalReport,
fulfilling the requirement: "generate orders that link items with a technical report"
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    String, DateTime, Numeric, Integer, ForeignKey, 
    func, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base

if TYPE_CHECKING:
    from models.item import Item
    from models.technical_report import TechnicalReport


class OrderStatus(str, Enum):
    """Enum for order status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(Base):
    """
    Order model for maintenance service orders.
    
    KEY DESIGN: Links items (spare parts) with a TechnicalReport entity.
    This fulfills: "generate orders that link items with a technical report"
    
    Relationships:
    - Order -> TechnicalReport (N:1 or 1:1)
    - Order -> OrderItems -> Items (N:M through junction table)
    
    Implements idempotency through unique request_id constraint.
    
    Attributes:
        id: Primary key
        request_id: Unique identifier from client (for idempotency)
        technical_report_id: FK to TechnicalReport entity
        status: Current order status
        image_url: URL to maintenance image in S3 (optional)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    request_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,  # Ensures idempotency
        nullable=False,
        index=True,
        comment="Client-provided unique ID for idempotency"
    )
    
    # IMPORTANT: This links the order to a TechnicalReport entity
    technical_report_id: Mapped[int] = mapped_column(
        ForeignKey("technical_reports.id", ondelete="RESTRICT"),
        nullable=False,
        comment="FK to the technical report linked with this order's items"
    )
    
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.PENDING,
        nullable=False
    )
    
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True,
        comment="S3 URL for maintenance image"
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
    
    # Link to TechnicalReport - THE KEY RELATIONSHIP
    technical_report: Mapped["TechnicalReport"] = relationship(
        "TechnicalReport",
        back_populates="order",
        lazy="joined"
    )
    
    # Link to Items through OrderItem junction table
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    @property
    def total_amount(self) -> Decimal:
        """Calculate total order amount."""
        return sum(
            (item.unit_price * item.quantity for item in self.items),
            Decimal("0.00")
        )
    
    def __repr__(self) -> str:
        return f"<Order(id={self.id}, request_id='{self.request_id}', status='{self.status}')>"


class OrderItem(Base):
    """
    OrderItem model - junction table linking Orders with Items (spare parts).
    
    This enables the N:M relationship between Orders and Items,
    storing quantity and price snapshot at time of order.
    
    Attributes:
        id: Primary key
        order_id: Foreign key to order
        item_id: Foreign key to item (spare part)
        quantity: Quantity of items
        unit_price: Price at time of order (snapshot)
    """
    
    __tablename__ = "order_items"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), 
        nullable=False,
        comment="Price snapshot at time of order"
    )
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    item: Mapped["Item"] = relationship("Item", back_populates="order_items")
    
    @property
    def subtotal(self) -> Decimal:
        """Calculate item subtotal."""
        return self.unit_price * self.quantity
    
    def __repr__(self) -> str:
        return f"<OrderItem(order_id={self.order_id}, item_id={self.item_id}, qty={self.quantity})>"