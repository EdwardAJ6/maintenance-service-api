"""
Pydantic schemas for Category validation and serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class CategoryBase(BaseModel):
    """Base schema for Category with common fields."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Category name",
        examples=["Electrónica"]
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Category description",
        examples=["Componentes y repuestos electrónicos"]
    )


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""
    pass


class CategoryResponse(CategoryBase):
    """Schema for category response."""
    
    id: int = Field(..., description="Category ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class CategoryInItem(BaseModel):
    """Simplified category schema for embedding in item responses."""
    
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)
