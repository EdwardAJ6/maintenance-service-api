"""
TechnicalReport model for maintenance reports.
Represents the technical documentation linked to maintenance orders.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base

if TYPE_CHECKING:
    from models.user import User
    from models.order import Order


class TechnicalReport(Base):
    """
    Technical Report entity for maintenance diagnostics.
    
    This entity fulfills the requirement:
    "generate orders that LINK items with a TECHNICAL REPORT"
    
    By having TechnicalReport as a separate entity, we achieve:
    - Clear separation of concerns
    - Audit trail (who created the report)
    - Extensibility (diagnosis, recommendations, etc.)
    - Proper relational design
    
    Attributes:
        id: Primary key
        title: Report title/summary
        description: Detailed description of the maintenance work
        diagnosis: Technical diagnosis of the issue
        recommendations: Recommended future actions
        created_by_id: User who created the report (FK)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "technical_reports"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    title: Mapped[str] = mapped_column(
        String(200), 
        nullable=False,
        comment="Brief title/summary of the report"
    )
    
    description: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        comment="Detailed description of maintenance performed"
    )
    
    diagnosis: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="Technical diagnosis of the issue found"
    )
    
    recommendations: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="Recommendations for future maintenance"
    )
    
    # Audit: who created this report
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created the report"
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
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="technical_reports",
        lazy="joined"
    )
    
    # One report can be linked to one order (1:1)
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        back_populates="technical_report",
        uselist=False,
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<TechnicalReport(id={self.id}, title='{self.title[:30]}...')>"