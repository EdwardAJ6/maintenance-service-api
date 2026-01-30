from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Optional, Annotated
from services.auth_service import decode_token
from schemas.user import TokenData

security = HTTPBearer(description="JWT token for authentication")


async def get_current_user(
    credentials: Annotated = Depends(security),
) -> TokenData:
    """Obtener usuario actual desde el token JWT en header Authorization."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    token_data = decode_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


async def get_current_admin(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """Verificar que el usuario actual sea admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    
    return current_user
