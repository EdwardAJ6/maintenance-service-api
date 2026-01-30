"""
Pydantic schemas for Item validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from schemas.category import CategoryInItem
from utils.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT


class ItemBase(BaseModel):
    """Base schema for Item with common fields."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Item name",
        examples=["Filtro de Aceite"]
    )
    sku: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Stock Keeping Unit",
        examples=["FIL-ACE-001"]
    )
    price: Decimal = Field(
        ...,
        gt=0,
        description="Item price (2 decimal places)",
        examples=[25.99]
    )
    stock: int = Field(
        ...,
        ge=0,
        description="Current stock quantity",
        examples=[100]
    )
    category_id: Optional[int] = Field(
        None,
        description="Category ID (optional)",
        examples=[1]
    )
    
    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        """Ensure price is converted to Decimal."""
        if v is not None:
            return Decimal(str(v))
        return v


class ItemCreate(ItemBase):
    """Schema for creating a new item."""
    pass


class ItemUpdate(BaseModel):
    """
    Schema for partial item update (PATCH).
    All fields are optional to support partial updates.
    """
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Item name"
    )
    price: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Item price"
    )
    stock: Optional[int] = Field(
        None,
        ge=0,
        description="Current stock quantity"
    )
    category_id: Optional[int] = Field(
        None,
        description="Category ID"
    )
    
    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        """Ensure price is converted to Decimal."""
        if v is not None:
            return Decimal(str(v))
        return v


class ItemResponse(BaseModel):
    """Schema for item response with category information (LEFT JOIN)."""
    
    id: int = Field(..., description="Item ID")
    name: str = Field(..., description="Item name")
    sku: str = Field(..., description="Stock Keeping Unit")
    price: Decimal = Field(..., description="Item price")
    stock: int = Field(..., description="Current stock quantity")
    category_id: Optional[int] = Field(None, description="Category ID")
    category: Optional[CategoryInItem] = Field(
        None,
        description="Category information (from LEFT JOIN)"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ItemInOrder(BaseModel):
    """Simplified item schema for order responses."""
    
    id: int
    name: str
    sku: str
    
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Query parameters for pagination."""
    
    skip: int = Field(
        0,
        ge=0,
        description="Number of records to skip",
        examples=[0]
    )
    limit: int = Field(
        DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description=f"Number of records to return (max: {MAX_PAGE_LIMIT})",
        examples=[20]
    )
