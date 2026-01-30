from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """Schema para crear usuario."""
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """Schema para login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema de respuesta de usuario (sin contraseña)."""
    id: int
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema de respuesta de autenticación."""
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    """Schema de datos dentro del JWT."""
    email: Optional[str] = None
    user_id: Optional[int] = None
    is_admin: Optional[bool] = False
