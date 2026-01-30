"""
Servicio de inicialización de datos por defecto.
"""
from sqlalchemy.orm import Session
from models.user import User
from services.auth_service import hash_password
from config import get_settings


def init_admin_user(db: Session) -> User:
    """
    Crear usuario admin por defecto si no existe.
    Lee credenciales desde variables de entorno.
    """
    settings = get_settings()
    
    # Verificar si el admin ya existe
    admin = db.query(User).filter(User.email == settings.admin_email).first()
    if admin:
        return admin
    
    # Crear admin
    admin = User(
        email=settings.admin_email,
        hashed_password=hash_password(settings.admin_password),
        is_admin=True,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    return admin
