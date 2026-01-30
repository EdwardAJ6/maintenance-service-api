from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from schemas.user import TokenData

# Configuración de hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Variables que se cargan desde config
SECRET_KEY: str = None 
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


def set_secret_key(key: str):
    """Establecer la clave secreta para JWT."""
    global SECRET_KEY
    SECRET_KEY = key


def hash_password(password: str) -> str:
    """Hashear contraseña."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Crear token JWT."""
    if SECRET_KEY is None:
        raise RuntimeError("SECRET_KEY not set. Call set_secret_key() first.")
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decodificar y validar token JWT."""
    if SECRET_KEY is None:
        raise RuntimeError("SECRET_KEY not set. Call set_secret_key() first.")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        is_admin: bool = payload.get("is_admin", False)
        
        if email is None or user_id is None:
            return None
        
        return TokenData(email=email, user_id=user_id, is_admin=is_admin)
    except JWTError:
        return None
