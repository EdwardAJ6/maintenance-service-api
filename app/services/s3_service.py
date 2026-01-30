"""
AWS S3 Service module for image upload.
Supports both simulated mode (DEBUG=True) and real S3 (DEBUG=False).
"""

import base64
import uuid
import logging
from typing import Optional
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from botocore.client import BaseClient

from config import get_settings
from utils import get_logger

logger = get_logger(__name__)


class S3ServiceError(Exception):
    """Custom exception for S3 service errors."""
    pass


class S3ConfigurationError(S3ServiceError):
    """Raised when S3 configuration is missing or invalid."""
    pass


class S3Service:
    """
    Service class for AWS S3 operations.
    
    Behavior depends on DEBUG setting:
    - DEBUG=True: Simulates S3 operations (no real uploads)
    - DEBUG=False: Real S3 operations (requires valid AWS credentials)
    """
    
    def __init__(self) -> None:
        """Initialize S3 service."""
        self._settings = get_settings()
        self._client: Optional[BaseClient] = None
        self._is_simulation: bool = self._settings.debug
        
        # Validate configuration on init if not in simulation mode
        if not self._is_simulation:
            self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """
        Validate required AWS configuration.
        
        Raises:
            S3ConfigurationError: If required configuration is missing
        """
        missing = []
        
        if not self._settings.aws_access_key_id:
            missing.append("AWS_ACCESS_KEY_ID")
        if not self._settings.aws_secret_access_key:
            missing.append("AWS_SECRET_ACCESS_KEY")
        if not self._settings.s3_bucket_name:
            missing.append("S3_BUCKET_NAME")
        
        if missing:
            raise S3ConfigurationError(
                f"Missing required AWS configuration: {', '.join(missing)}. "
                "Set DEBUG=True for simulation mode or provide valid credentials."
            )
    
    @property
    def client(self) -> BaseClient:
        """
        Lazy initialization of S3 client.
        
        Returns:
            boto3 S3 client instance
        """
        if self._client is None:
            self._client = boto3.client(
                "s3",
                region_name=self._settings.aws_region,
                aws_access_key_id=self._settings.aws_access_key_id,
                aws_secret_access_key=self._settings.aws_secret_access_key
            )
        return self._client
    
    def _generate_key(self, order_id: str, extension: str = "jpg") -> str:
        """
        Generate a unique S3 object key.
        
        Args:
            order_id: The order ID associated with the image
            extension: File extension
            
        Returns:
            Unique S3 object key
        """
        timestamp: str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id: str = uuid.uuid4().hex[:8]
        return f"maintenance-images/{order_id}/{timestamp}_{unique_id}.{extension}"
    
    def _get_extension(self, content_type: str) -> str:
        """Get file extension from content type."""
        extensions: dict[str, str] = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp"
        }
        return extensions.get(content_type, "jpg")
    
    def _build_url(self, object_key: str) -> str:
        """Build S3 URL for an object."""
        return (
            f"https://{self._settings.s3_bucket_name}"
            f".s3.{self._settings.aws_region}.amazonaws.com/{object_key}"
        )
    
    def upload_image(
        self,
        image_base64: str,
        order_id: str,
        content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload a base64 encoded image to S3.
        
        Args:
            image_base64: Base64 encoded image data
            order_id: Order ID for organizing images
            content_type: MIME type of the image
            
        Returns:
            S3 URL of the uploaded image
            
        Raises:
            S3ServiceError: If upload fails
        """
        # Decode base64
        try:
            image_data = base64.b64decode(image_base64)
        except Exception as e:
            raise S3ServiceError(f"Invalid base64 image data: {e}")
        
        extension = self._get_extension(content_type)
        object_key = self._generate_key(order_id, extension)
        
        # Simulation mode
        if self._is_simulation:
            logger.info(
                f"[S3 SIMULATION] Upload: s3://{self._settings.s3_bucket_name}/{object_key} "
                f"({len(image_data)} bytes)"
            )
            return self._build_url(object_key)
        
        # Real S3 upload
        try:
            self.client.put_object(
                Bucket=self._settings.s3_bucket_name,
                Key=object_key,
                Body=image_data,
                ContentType=content_type,
                Metadata={
                    "order_id": order_id,
                    "uploaded_at": datetime.utcnow().isoformat()
                }
            )
            logger.info(f"[S3] Uploaded: {object_key}")
            return self._build_url(object_key)
            
        except NoCredentialsError:
            raise S3ServiceError("AWS credentials not configured")
        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise S3ServiceError(f"S3 upload failed: {error_msg}")
        except BotoCoreError as e:
            raise S3ServiceError(f"AWS service error: {e}")
    
    def delete_image(self, object_key: str) -> bool:
        """
        Delete an image from S3.
        
        Args:
            object_key: S3 object key to delete
            
        Returns:
            True if successful
            
        Raises:
            S3ServiceError: If deletion fails
        """
        if self._is_simulation:
            logger.info(f"[S3 SIMULATION] Delete: {object_key}")
            return True
        
        try:
            self.client.delete_object(
                Bucket=self._settings.s3_bucket_name,
                Key=object_key
            )
            logger.info(f"[S3] Deleted: {object_key}")
            return True
        except ClientError as e:
            error_msg: str = e.response.get("Error", {}).get("Message", str(e))
            raise S3ServiceError(f"Delete failed: {error_msg}")
    
    def get_presigned_url(self, object_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access.
        
        Args:
            object_key: S3 object key
            expiration: URL expiration in seconds (default: 1 hour)
            
        Returns:
            Presigned URL
            
        Raises:
            S3ServiceError: If URL generation fails
        """
        if self._is_simulation:
            url: str = f"{self._build_url(object_key)}?X-Amz-Expires={expiration}"
            logger.info(f"[S3 SIMULATION] Presigned URL: {object_key}")
            return url
        
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._settings.s3_bucket_name,
                    "Key": object_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise S3ServiceError(f"Presigned URL failed: {error_msg}")


# Singleton
_s3_service: Optional[S3Service] = None


def get_s3_service() -> S3Service:
    """Get or create S3 service singleton."""
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service