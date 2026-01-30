"""
Orders router for maintenance order management.
Implements idempotency through unique request_id.

KEY FEATURE: Orders LINK items (spare parts) with TechnicalReport entities,
fulfilling: "generate orders that link items with a technical report"
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from database import get_db, DBManager
from models import Order, OrderItem, Item, OrderStatus, TechnicalReport
from schemas import OrderCreate, OrderResponse, OrderListResponse
from services import get_s3_service, S3ServiceError
from utils import measure_time, get_logger, ERROR_MESSAGES, DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, VALID_STATUS_TRANSITIONS
from utils.security import get_current_user
from schemas.user import TokenData

logger = get_logger(__name__)

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    responses={404: {"description": "Order not found"}}
)

# Initialize DBManagers
order_manager = DBManager(Order)
item_manager = DBManager(Item)
report_manager = DBManager(TechnicalReport)


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new maintenance order",
    description="""
    Create a new maintenance order that LINKS items (spare parts) with a technical report.
    
    This endpoint creates:
    1. A TechnicalReport entity (with diagnosis, recommendations, etc.)
    2. An Order that links the report with the requested items
    
    **Idempotency**: If you send the same `request_id` multiple times, 
    subsequent requests will return the existing order with status 200 OK.
    """
)
@measure_time
async def create_order(
    order: OrderCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Order:
    """
    Create a new maintenance order linking items with a technical report.
    
    - **request_id**: Unique client-provided identifier for idempotency
    - **technical_report**: Technical report data (title, description, diagnosis, recommendations)
    - **items**: List of items (spare parts) to link with the technical report
    - **image_base64**: Optional base64 encoded maintenance image for S3 upload
    """
    # Check for existing order with same request_id (IDEMPOTENCY)
    existing_order = order_manager.get_by_field(db, "request_id", order.request_id)
    
    if existing_order is not None:
        logger.info(
            f"Idempotent request: Order with request_id '{order.request_id}' "
            f"already exists (id={existing_order.id})"
        )
        response.status_code = status.HTTP_200_OK
        
        # Reload with relationships
        existing_order = (
            db.query(Order)
            .options(
                joinedload(Order.technical_report),
                joinedload(Order.items).joinedload(OrderItem.item)
            )
            .filter(Order.id == existing_order.id)
            .first()
        )
        return existing_order
    
    # Validate items list is not empty
    if not order.items or len(order.items) == 0:
        logger.warning(f"Attempt to create order with empty items list")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES["order_items_empty"]
        )
    
    # Validate all items exist and have sufficient stock
    order_items_data = []
    for order_item in order.items:
        if order_item.quantity <= 0:
            logger.warning(f"Invalid quantity: {order_item.quantity}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES["order_invalid_quantity"]
            )
        
        db_item = item_manager.get(db, id=order_item.item_id)
        
        if db_item is None:
            logger.warning(f"Item not found: {order_item.item_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES["order_item_not_found"].format(item_id=order_item.item_id)
            )
        
        if db_item.stock < order_item.quantity:
            logger.warning(
                f"Insufficient stock: Item {order_item.item_id}, "
                f"Available: {db_item.stock}, Requested: {order_item.quantity}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES["order_insufficient_stock"].format(
                    item_id=order_item.item_id,
                    available=db_item.stock,
                    requested=order_item.quantity
                )
            )
        
        order_items_data.append({
            "item": db_item,
            "quantity": order_item.quantity,
            "unit_price": db_item.price
        })
    
    # Handle optional image upload to S3
    image_url = None
    if order.image_base64 is not None:
        try:
            s3_service = get_s3_service()
            image_url = s3_service.upload_image(
                image_base64=order.image_base64,
                order_id=order.request_id
            )
            logger.info(f"Image uploaded to S3: {image_url}")
        except S3ServiceError as e:
            logger.warning(f"S3 upload failed (continuing without image): {str(e)}")
    
    try:
        # STEP 1: Create the TechnicalReport entity first
        db_report = TechnicalReport(
            title=order.technical_report.title,
            description=order.technical_report.description,
            diagnosis=order.technical_report.diagnosis,
            recommendations=order.technical_report.recommendations,
            created_by_id=current_user.user_id  # Track who created the report
        )
        db.add(db_report)
        db.flush()  # Get the report ID
        
        logger.info(f"TechnicalReport created: id={db_report.id}, title='{db_report.title}'")
        
        # STEP 2: Create the Order that LINKS items with the report
        db_order = Order(
            request_id=order.request_id,
            technical_report_id=db_report.id,  # Link to the technical report
            status=OrderStatus.PENDING,
            image_url=image_url
        )
        db.add(db_order)
        db.flush()  # Get the order ID
        
        # STEP 3: Create order items (linking the items/spare parts)
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=db_order.id,
                item_id=item_data["item"].id,
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"]
            )
            db.add(order_item)
            
            # Decrease stock
            item_manager.update(
                db,
                id=item_data["item"].id,
                stock=item_data["item"].stock - item_data["quantity"]
            )
        
        db.commit()
        db.refresh(db_order)
        
        logger.info(
            f"Order created: id={db_order.id}, request_id={order.request_id}, "
            f"technical_report_id={db_report.id}, items_count={len(order_items_data)}"
        )
        
    except IntegrityError as e:
        db.rollback()
        existing = order_manager.get_by_field(db, "request_id", order.request_id)
        
        if existing is not None:
            logger.info(f"Race condition detected: Order {order.request_id} already exists")
            response.status_code = status.HTTP_200_OK
            existing = (
                db.query(Order)
                .options(
                    joinedload(Order.technical_report),
                    joinedload(Order.items).joinedload(OrderItem.item)
                )
                .filter(Order.id == existing.id)
                .first()
            )
            return existing
        
        logger.error(f"IntegrityError creating order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_integrity_error"].format(detail="Failed to create order")
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to create order")
        )
    
    # Reload with all relationships for response
    db_order = (
        db.query(Order)
        .options(
            joinedload(Order.technical_report),
            joinedload(Order.items).joinedload(OrderItem.item)
        )
        .filter(Order.id == db_order.id)
        .first()
    )
    
    return db_order


@router.get(
    "/",
    response_model=List[OrderListResponse],
    summary="List all orders",
    description="Retrieve a list of all maintenance orders with their linked technical reports."
)
@measure_time
async def get_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT, description=f"Maximum records to return (max: {MAX_PAGE_LIMIT})"),
    status_filter: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> List[Order]:
    """Retrieve all orders with optional filtering."""
    try:
        query = db.query(Order).options(
            joinedload(Order.technical_report),
            joinedload(Order.items).joinedload(OrderItem.item)
        )
        
        if status_filter is not None:
            query = query.filter(Order.status == status_filter)
        
        orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
        
        logger.info(f"Orders retrieved: {len(orders)} orders (skip={skip}, limit={limit})")
        return orders
    
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to retrieve orders")
        )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
    description="Retrieve a specific maintenance order with its linked technical report and items."
)
@measure_time
async def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Order:
    """Retrieve an order by ID with technical report and all items."""
    try:
        db_order = (
            db.query(Order)
            .options(
                joinedload(Order.technical_report),
                joinedload(Order.items).joinedload(OrderItem.item)
            )
            .filter(Order.id == order_id)
            .first()
        )
        
        if db_order is None:
            logger.warning(f"Order not found: {order_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES["order_not_found"].format(order_id=order_id)
            )
        
        return db_order
    
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving order {order_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to retrieve order")
        )


@router.get(
    "/request/{request_id}",
    response_model=OrderResponse,
    summary="Get order by request ID",
    description="Retrieve a maintenance order by its client-provided request_id."
)
@measure_time
async def get_order_by_request_id(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Order:
    """Retrieve an order by its request_id (idempotency key)."""
    try:
        db_order = (
            db.query(Order)
            .options(
                joinedload(Order.technical_report),
                joinedload(Order.items).joinedload(OrderItem.item)
            )
            .filter(Order.request_id == request_id)
            .first()
        )
        
        if db_order is None:
            logger.warning(f"Order not found by request_id: {request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES["order_request_id_not_found"].format(request_id=request_id)
            )
        
        return db_order
    
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving order by request_id {request_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to retrieve order")
        )


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status",
    description="Update the status of a maintenance order."
)
@measure_time
async def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
) -> Order:
    """Update the status of an order."""
    try:
        db_order = (
            db.query(Order)
            .options(
                joinedload(Order.technical_report),
                joinedload(Order.items).joinedload(OrderItem.item)
            )
            .filter(Order.id == order_id)
            .first()
        )
        
        if db_order is None:
            logger.warning(f"Order not found: {order_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES["order_not_found"].format(order_id=order_id)
            )
        
        # Validate status transition
        current_status = db_order.status.value if hasattr(db_order.status, 'value') else str(db_order.status)
        new_status_str = new_status.value if hasattr(new_status, 'value') else str(new_status)
        
        valid_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])
        if new_status_str not in valid_transitions:
            logger.warning(f"Invalid status transition: {current_status} -> {new_status_str}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES["order_invalid_status"].format(
                    current_status=current_status,
                    new_status=new_status_str
                )
            )
        
        # If cancelling, restore stock
        if new_status_str == "cancelled" and current_status != "cancelled":
            for order_item in db_order.items:
                item_manager.update(
                    db,
                    id=order_item.item_id,
                    stock=order_item.item.stock + order_item.quantity
                )
            logger.info(f"Order {order_id} cancelled, stock restored")
        
        # Update order status
        order_manager.update(db, id=order_id, status=new_status)
        
        logger.info(f"Order {order_id} status updated: {current_status} -> {new_status_str}")
        
        # Reload with relationships
        db_order = (
            db.query(Order)
            .options(
                joinedload(Order.technical_report),
                joinedload(Order.items).joinedload(OrderItem.item)
            )
            .filter(Order.id == order_id)
            .first()
        )
        
        return db_order
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating order {order_id} status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["database_error"].format(detail="Failed to update order status")
        )