"""
Categories router for category management endpoints.
Uses DBManager for database operations.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from database import get_db, DBManager
from models import Category
from schemas import CategoryCreate, CategoryResponse
from utils import measure_time, get_logger, ERROR_MESSAGES, DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from utils.security import get_current_user
from schemas.user import TokenData

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
    responses={404: {"description": "Category not found"}}
)

logger = get_logger(__name__)

# Initialize DBManager for Category model
category_manager = DBManager(Category)


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new category",
    description="Create a new category for organizing items/spare parts."
)
@measure_time
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Category:
    """
    Create a new category.
    
    - **name**: Category name (required, unique)
    - **description**: Optional category description
    """
    try:
        db_category = category_manager.create(db, **category.model_dump())
        logger.info(f"Category created successfully: {db_category.id} (name: {db_category.name}) by user {current_user.email}")
        return db_category
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with name '{category.name}' already exists"
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to create category")
        )


@router.get(
    "/",
    response_model=List[CategoryResponse],
    summary="List all categories",
    description="Retrieve a list of all categories."
)
@measure_time
async def get_categories(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT, description=f"Maximum records to return (max: {MAX_PAGE_LIMIT})"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> List[Category]:
    """
    Retrieve all categories with pagination.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: {DEFAULT_PAGE_LIMIT}, max: {MAX_PAGE_LIMIT})
    """
    try:
        categories = category_manager.list(db, skip=skip, limit=limit)
        logger.info(f"Categories retrieved: {len(categories)} categories (skip={skip}, limit={limit}) by user {current_user.email}")
        return categories
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to retrieve categories")
        )


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get category by ID",
    description="Retrieve a specific category by its ID."
)
@measure_time
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Category:
    """
    Retrieve a category by ID.
    
    - **category_id**: The ID of the category to retrieve
    """
    try:
        db_category = category_manager.get(db, id=category_id)
        
        # Using 'is None' for identity comparison (Pythonic)
        if db_category is None:
            logger.warning(f"Category not found: {category_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES["category_not_found"].format(category_id=category_id)
            )
        
        return db_category
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving category {category_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to retrieve category")
        )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
    description="Delete a category by its ID."
)
@measure_time
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> None:
    """
    Delete a category.
    
    - **category_id**: The ID of the category to delete
    """
    try:
        deleted = category_manager.delete(db, id=category_id)
        
        if not deleted:
            logger.warning(f"Attempt to delete non-existent category: {category_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES["category_not_found"].format(category_id=category_id)
            )
        
        logger.info(f"Category deleted successfully: {category_id} by user {current_user.email}")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error deleting category {category_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERROR_MESSAGES["category_not_deleted_has_items"].format(category_id=category_id)
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error deleting category {category_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to delete category")
        )
