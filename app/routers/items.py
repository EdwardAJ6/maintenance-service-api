"""
Items router for spare parts management endpoints.
Implements B-Tree indexed searches and LEFT JOIN with categories.
Uses DBManager for database operations.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from database import get_db, DBManager
from models import Item, Category
from schemas import ItemCreate, ItemUpdate, ItemResponse
from utils import measure_time, get_logger, ERROR_MESSAGES, DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from utils.security import get_current_user
from schemas.user import TokenData

router = APIRouter(
    prefix="/items",
    tags=["Items"],
    responses={404: {"description": "Item not found"}}
)

logger = get_logger(__name__)

# Initialize DBManagers
item_manager = DBManager(Item)
category_manager = DBManager(Category)


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item",
    description="Register a new spare part/item in the inventory."
)
@measure_time
async def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Item:
    """
    Create a new item/spare part.
    
    - **name**: Item name (required)
    - **sku**: Stock Keeping Unit (required, unique)
    - **price**: Item price (required, > 0)
    - **stock**: Current stock quantity (required, >= 0)
    - **category_id**: Optional category ID
    """
    try:
        # Validate category exists if provided
        if item.category_id is not None:
            category = category_manager.get(db, id=item.category_id)
            
            if category is None:
                logger.warning(f"Attempt to create item with non-existent category: {item.category_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES["item_invalid_category"].format(category_id=item.category_id)
                )
        
        db_item = item_manager.create(db, **item.model_dump())
        logger.info(f"Item created successfully: {db_item.id} (SKU: {db_item.sku})")
        return db_item
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERROR_MESSAGES["item_sku_exists"].format(sku=item.sku)
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to create item")
        )


@router.get(
    "/",
    response_model=List[ItemResponse],
    summary="List all items",
    description="Retrieve a list of all items with category information (LEFT JOIN)."
)
@measure_time
async def get_items(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT, description=f"Maximum records to return (max: {MAX_PAGE_LIMIT})"),
    sku: Optional[str] = Query(None, description="Filter by SKU (uses B-Tree index)"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> List[Item]:
    """
    Retrieve all items with category information via LEFT JOIN.
    
    The query uses joinedload for eager loading of the category relationship,
    which translates to a LEFT JOIN in SQL.
    
    - **skip**: Number of records to skip (default: {DEFAULT_PAGE_LIMIT})
    - **limit**: Maximum number of records to return (default: {DEFAULT_PAGE_LIMIT}, max: {MAX_PAGE_LIMIT})
    - **sku**: Optional SKU filter (uses B-Tree index for optimization)
    - **category_id**: Optional category filter
    """
    try:
        # Build query with LEFT JOIN (joinedload)
        query = db.query(Item).options(joinedload(Item.category))
        
        # Apply SKU filter if provided (uses B-Tree index)
        if sku is not None:
            query = query.filter(Item.sku == sku)
        
        # Apply category filter if provided
        if category_id is not None:
            query = query.filter(Item.category_id == category_id)
        
        # Apply pagination and execute
        items = query.offset(skip).limit(limit).all()
        
        logger.info(f"Items retrieved: {len(items)} items (skip={skip}, limit={limit})")
        return items
    
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to retrieve items")
        )


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item by ID",
    description="Retrieve a specific item by its ID with category information."
)
@measure_time
async def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Item:
    """
    Retrieve an item by ID with category information.
    
    - **item_id**: The ID of the item to retrieve
    """
    try:
        db_item = (
            db.query(Item)
            .options(joinedload(Item.category))
            .filter(Item.id == item_id)
            .first()
        )
        
        # Using 'is None' for identity comparison (Pythonic)
        if db_item is None:
            logger.warning(f"Item not found: {item_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES["item_not_found"].format(item_id=item_id)
            )
        
        return db_item
    
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to retrieve item")
        )


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item partially",
    description="Partially update an item (stock, price, etc.). Only provided fields are updated."
)
@measure_time
async def update_item(
    item_id: int,
    item_update: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Item:
    """
    Partially update an item (PATCH).
    
    Unlike PUT, PATCH only updates the fields that are provided.
    This endpoint is useful for updating stock or price without
    requiring all item fields.
    
    - **item_id**: The ID of the item to update
    - **name**: New item name (optional)
    - **price**: New price (optional)
    - **stock**: New stock quantity (optional)
    - **category_id**: New category ID (optional)
    """
    try:
        # Check if item exists
        if not item_manager.exists(db, id=item_id):
            logger.warning(f"Attempt to update non-existent item: {item_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES["item_not_found"].format(item_id=item_id)
            )
        
        # Get only the fields that were explicitly set (not None)
        update_data = item_update.model_dump(exclude_unset=True)
        
        # Validate category if being updated
        if "category_id" in update_data and update_data["category_id"] is not None:
            category = category_manager.get(db, id=update_data["category_id"])
            
            if category is None:
                logger.warning(f"Attempt to update item with non-existent category: {update_data['category_id']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES["item_invalid_category"].format(category_id=update_data["category_id"])
                )
        
        db_item = item_manager.update(db, id=item_id, **update_data)
        
        # Reload with category relationship
        db_item = (
            db.query(Item)
            .options(joinedload(Item.category))
            .filter(Item.id == item_id)
            .first()
        )
        
        logger.info(f"Item updated successfully: {item_id}")
        return db_item
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error updating item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERROR_MESSAGES["database_integrity_error"].format(detail="Update failed")
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to update item")
        )


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
    description="Delete an item by its ID."
)
@measure_time
async def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> None:
    """
    Delete an item.
    
    - **item_id**: The ID of the item to delete
    """
    try:
        deleted = item_manager.delete(db, id=item_id)
        
        if not deleted:
            logger.warning(f"Attempt to delete non-existent item: {item_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES["item_not_found"].format(item_id=item_id)
            )
        
        logger.info(f"Item deleted successfully: {item_id}")
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error deleting item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete item: it is referenced by existing orders"
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error deleting item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to delete item")
        )


@router.get(
    "/search/sku/{sku}",
    response_model=ItemResponse,
    summary="Search item by SKU",
    description="Search for an item using SKU (optimized with B-Tree index)."
)
@measure_time
async def search_by_sku(
    sku: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Item:
    """
    Search for an item by exact SKU match.
    
    This endpoint is optimized with a B-Tree index on the SKU column
    for fast lookups.
    
    - **sku**: The SKU to search for
    """
    try:
        db_item = (
            db.query(Item)
            .options(joinedload(Item.category))
            .filter(Item.sku == sku)  # Uses B-Tree index
            .first()
        )
        
        if db_item is None:
            logger.warning(f"Item not found with SKU: {sku}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with SKU '{sku}' not found"
            )
        
        return db_item
    
    except SQLAlchemyError as e:
        logger.error(f"Database error searching item by SKU {sku}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to search item")
        )
