"""
Pydantic schemas for Order validation and serialization.
Orders link items (spare parts) with technical reports.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

from models.order import OrderStatus
from schemas.item import ItemInOrder
from schemas.technical_report import TechnicalReportCreate, TechnicalReportInOrder


class OrderItemCreate(BaseModel):
    """Schema for creating an order item."""
    
    item_id: int = Field(..., description="Item ID", examples=[1])
    quantity: int = Field(
        ...,
        gt=0,
        description="Quantity of items",
        examples=[2]
    )


class OrderItemResponse(BaseModel):
    """Schema for order item response."""
    
    id: int = Field(..., description="Order item ID")
    item_id: int = Field(..., description="Item ID")
    item: ItemInOrder = Field(..., description="Item details")
    quantity: int = Field(..., description="Quantity")
    unit_price: Decimal = Field(..., description="Unit price at time of order")
    subtotal: Decimal = Field(..., description="Item subtotal")
    
    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """
    Schema for creating a new order.
    
    Links items (spare parts) with a technical report.
    
    The request_id is required for idempotency - if the same request_id
    is sent twice, the second request will return the existing order
    instead of creating a duplicate.
    """
    
    request_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique request identifier for idempotency",
        examples=["ORD-2024-001"]
    )
    technical_report: TechnicalReportCreate = Field(
        ...,
        description="Technical report data - the report that will be linked with the items"
    )
    items: List[OrderItemCreate] = Field(
        ...,
        min_length=1,
        description="List of items (spare parts) to link with the technical report"
    )
    image_base64: Optional[str] = Field(
        None,
        description="Base64 encoded image for S3 upload (optional)"
    )


class OrderResponse(BaseModel):
    """Schema for order response."""
    
    id: int = Field(..., description="Order ID")
    request_id: str = Field(..., description="Client request ID")
    technical_report: TechnicalReportInOrder = Field(
        ..., 
        description="Linked technical report"
    )
    status: OrderStatus = Field(..., description="Order status")
    image_url: Optional[str] = Field(None, description="S3 image URL")
    items: List[OrderItemResponse] = Field(
        ..., 
        description="Order items (spare parts) linked to the technical report"
    )
    total_amount: Decimal = Field(..., description="Total order amount")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    """Simplified schema for order listing."""
    
    id: int
    request_id: str
    technical_report: TechnicalReportInOrder = Field(..., description="Linked technical report")
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)