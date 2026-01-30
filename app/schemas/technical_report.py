"""
Pydantic schemas for TechnicalReport validation and serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class TechnicalReportBase(BaseModel):
    """Base schema for TechnicalReport."""
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Report title/summary",
        examples=["Mantenimiento preventivo motor diesel"]
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Detailed description of maintenance work",
        examples=["Revisión completa del sistema de refrigeración y cambio de filtros"]
    )
    diagnosis: Optional[str] = Field(
        None,
        description="Technical diagnosis of the issue",
        examples=["Motor presenta ruido anormal en cilindro 3. Desgaste en válvulas."]
    )
    recommendations: Optional[str] = Field(
        None,
        description="Future maintenance recommendations",
        examples=["Programar revisión en 5000 km. Verificar nivel de aceite semanalmente."]
    )


class TechnicalReportCreate(TechnicalReportBase):
    """Schema for creating a new technical report."""
    pass


class TechnicalReportUpdate(BaseModel):
    """Schema for updating a technical report (partial)."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    diagnosis: Optional[str] = None
    recommendations: Optional[str] = None


class TechnicalReportResponse(TechnicalReportBase):
    """Schema for technical report response."""
    
    id: int = Field(..., description="Report ID")
    created_by_id: Optional[int] = Field(None, description="ID of user who created the report")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class TechnicalReportInOrder(BaseModel):
    """Simplified technical report schema for embedding in order responses."""
    
    id: int
    title: str
    description: str
    diagnosis: Optional[str] = None
    recommendations: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)