"""
Application-wide constants and configuration values.
"""

# Pagination constants
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100

# Item constants
MIN_ITEM_NAME_LENGTH = 1
MAX_ITEM_NAME_LENGTH = 200
MIN_SKU_LENGTH = 1
MAX_SKU_LENGTH = 50

# Order constants
DEFAULT_PRESIGNED_URL_EXPIRATION = 3600  # 1 hour in seconds

# Error messages
ERROR_MESSAGES = {
    # Item errors
    "item_not_found": "Item with id {item_id} not found",
    "item_sku_exists": "Item with SKU {sku} already exists",
    "item_invalid_price": "Price must be greater than 0",
    "item_invalid_stock": "Stock cannot be negative",
    "item_invalid_category": "Category with id {category_id} not found",
    "item_category_required": "Category ID is required when provided",
    
    # Category errors
    "category_not_found": "Category with id {category_id} not found",
    "category_name_required": "Category name is required",
    "category_not_deleted_has_items": "Cannot delete category {category_id}. It has items associated",
    
    # Order errors
    "order_not_found": "Order with id {order_id} not found",
    "order_request_id_not_found": "Order with request_id {request_id} not found",
    "order_items_empty": "Order must contain at least one item",
    "order_item_not_found": "Item with id {item_id} not found for order",
    "order_insufficient_stock": "Insufficient stock for item {item_id}. Available: {available}, Requested: {requested}",
    "order_invalid_quantity": "Quantity must be greater than 0",
    "order_invalid_status": "Invalid status transition from {current_status} to {new_status}",
    "order_cannot_cancel_completed": "Cannot cancel an order with status {status}",
    
    # Database errors
    "database_integrity_error": "Database constraint violation: {detail}",
    "database_error": "Database error occurred: {detail}",
    
    # S3 errors
    "s3_upload_error": "Failed to upload image to S3: {detail}",
    "s3_delete_error": "Failed to delete image from S3: {detail}",
    
    # Validation errors
    "validation_error": "Validation error: {detail}",
    "invalid_query_params": "Invalid query parameters: {detail}",
    
    # Server errors
    "internal_server_error": "An internal server error occurred",
}

# Order status constants
ORDER_STATUS_PENDING = "pending"
ORDER_STATUS_IN_PROGRESS = "in_progress"
ORDER_STATUS_COMPLETED = "completed"
ORDER_STATUS_CANCELLED = "cancelled"

VALID_ORDER_STATUSES = {
    ORDER_STATUS_PENDING,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_CANCELLED,
}

# Valid status transitions
VALID_STATUS_TRANSITIONS = {
    ORDER_STATUS_PENDING: [ORDER_STATUS_IN_PROGRESS, ORDER_STATUS_CANCELLED],
    ORDER_STATUS_IN_PROGRESS: [ORDER_STATUS_COMPLETED, ORDER_STATUS_CANCELLED],
    ORDER_STATUS_COMPLETED: [],
    ORDER_STATUS_CANCELLED: [],
}
