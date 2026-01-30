"""
Tests for S3 Service.
"""

import os
import pytest
import base64

# Ensure DEBUG mode for tests
os.environ["DEBUG"] = "True"

from services.s3_service import S3Service, S3ServiceError, S3ConfigurationError, get_s3_service


class TestS3Service:
    """Test suite for S3 Service."""

    def test_service_initialization_simulation_mode(self):
        """Test S3 service initializes in simulation mode."""
        os.environ["DEBUG"] = "True"
        service = S3Service()
        
        assert service._is_simulation is True

    def test_upload_image_simulation(self):
        """Test image upload in simulation mode."""
        os.environ["DEBUG"] = "True"
        service = S3Service()
        
        # Create a simple base64 image (1x1 pixel PNG)
        image_base64 = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
        
        url = service.upload_image(
            image_base64=image_base64,
            order_id="TEST-ORDER-001",
            content_type="image/png"
        )
        
        assert "maintenance-images" in url
        assert "TEST-ORDER-001" in url
        assert ".png" in url

    def test_upload_image_invalid_base64(self):
        """Test upload with invalid base64 raises error."""
        os.environ["DEBUG"] = "True"
        service = S3Service()
        
        with pytest.raises(S3ServiceError) as exc_info:
            service.upload_image(
                image_base64="not-valid-base64!!!",
                order_id="TEST-001"
            )
        
        assert "Invalid base64" in str(exc_info.value)

    def test_delete_image_simulation(self):
        """Test image deletion in simulation mode."""
        os.environ["DEBUG"] = "True"
        service = S3Service()
        
        result = service.delete_image("maintenance-images/TEST/image.jpg")
        
        assert result is True

    def test_get_presigned_url_simulation(self):
        """Test presigned URL generation in simulation mode."""
        os.environ["DEBUG"] = "True"
        service = S3Service()
        
        url = service.get_presigned_url(
            object_key="maintenance-images/TEST/image.jpg",
            expiration=3600
        )
        
        assert "X-Amz-Expires=3600" in url

    def test_generate_key_format(self):
        """Test generated key has correct format."""
        service = S3Service()
        
        key = service._generate_key("ORDER-123", "jpg")
        
        assert key.startswith("maintenance-images/ORDER-123/")
        assert key.endswith(".jpg")

    def test_get_extension_mapping(self):
        """Test content type to extension mapping."""
        service = S3Service()
        
        assert service._get_extension("image/jpeg") == "jpg"
        assert service._get_extension("image/png") == "png"
        assert service._get_extension("image/gif") == "gif"
        assert service._get_extension("image/webp") == "webp"
        assert service._get_extension("unknown/type") == "jpg"  # Default

    def test_build_url_format(self):
        """Test URL building format."""
        service = S3Service()
        
        url = service._build_url("test/path/image.jpg")
        
        assert "s3." in url
        assert "amazonaws.com" in url
        assert "test/path/image.jpg" in url

    def test_singleton_pattern(self):
        """Test get_s3_service returns same instance."""
        service1 = get_s3_service()
        service2 = get_s3_service()
        
        assert service1 is service2


class TestS3ServiceConfiguration:
    """Test S3 Service configuration validation."""

    def test_s3_service_in_debug_mode(self):
        """Test that S3 service works in debug mode."""
        os.environ["DEBUG"] = "True"
        service = S3Service()
        assert service._is_simulation is True
