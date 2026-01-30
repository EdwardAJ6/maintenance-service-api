"""
Main entry point for the Maintenance Service API.
FastAPI application configuration and router registration.
"""

from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db, database_exists, get_db
from routers import categories_router, items_router, orders_router
from routers.auth import router as auth_router
from utils import get_logger, configure_logging
from services.auth_service import set_secret_key
from services.init_service import init_admin_user

# Configure logging
configure_logging()
logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    Validates database existence and creates it if necessary.
    Initializes default admin user.
    """
    # Startup
    logger.info("Starting Maintenance Service API...")
    
    # Set JWT secret key
    set_secret_key(settings.secret_key)
    logger.info("JWT secret key configured")
    
    # Check if database exists
    if not database_exists():
        logger.info("Database does not exist. Creating new database...")
    else:
        logger.info("Database found.")
    
    # Initialize database (creates tables if they don't exist)
    init_db()
    logger.info("Database initialized successfully")
    
    # Initialize default admin user
    try:
        db = next(get_db())
        admin = init_admin_user(db)
        logger.info(f"Admin user initialized: {admin.email}")
    except Exception as e:
        logger.error(f"Failed to initialize admin user: {e}")
    finally:
        db.close()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Maintenance Service API...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
    ## Maintenance Service API
    
    A RESTful API for managing maintenance orders and spare parts inventory.
    
    ### Features
    
    * **Items Management**: CRUD operations for spare parts with category support
    * **Orders Management**: Create and manage maintenance orders with idempotency
    * **Categories**: Organize items into categories
    * **S3 Integration**: Upload maintenance images to AWS S3 (simulated)
    
    ### Key Concepts
    
    * **Idempotency**: The `/orders/` POST endpoint is idempotent. Using the same 
      `request_id` will return the existing order instead of creating a duplicate.
    * **B-Tree Index**: The `sku` column in items is indexed with B-Tree for 
      optimized search performance.
    * **LEFT JOIN**: Item listings include category information via LEFT JOIN.
    
    ### Technical Details
    
    * Built with FastAPI and SQLAlchemy
    * Uses Pydantic for data validation
    * Implements proper HTTP status codes
    * Performance monitoring via `@measure_time` decorator
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# Logging middleware for structured request/response logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log HTTP requests and responses with timing information."""
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Incoming request: {request.method} {request.url.path}",
        extra={"extra_data": {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
        }}
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        f"Request completed: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - Duration: {duration:.3f}s",
        extra={"extra_data": {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_seconds": duration,
        }}
    )
    
    return response

# CORS middleware configuration - restrict to allowed origins
allowed_origins = settings.allowed_origins or ["http://localhost:8000"]
if isinstance(allowed_origins, str):
    allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]

logger.info(f"CORS configuration: Allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Register routers
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(items_router)
app.include_router(orders_router)


@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Welcome endpoint with API information."
)
async def root():
    """
    Root endpoint returning API information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check if the API is running and healthy."
)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
