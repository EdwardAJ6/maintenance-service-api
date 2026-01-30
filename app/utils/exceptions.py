"""
Custom exception classes for the application.
"""

from typing import Optional


class AppException(Exception):
    """Base exception for the application."""
    
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ItemException(AppException):
    """Exception raised for item-related errors."""
    pass


class CategoryException(AppException):
    """Exception raised for category-related errors."""
    pass


class OrderException(AppException):
    """Exception raised for order-related errors."""
    pass


class DatabaseException(AppException):
    """Exception raised for database errors."""
    pass


class ValidationException(AppException):
    """Exception raised for validation errors."""
    pass


class S3ServiceException(AppException):
    """Exception raised for S3 service errors."""
    pass