"""
Tests for utilities (decorators, config).
"""

import os
import time
import pytest
from unittest.mock import patch

from utils.decorators import measure_time
from config import Settings, get_settings


class TestMeasureTimeDecorator:
    """Test suite for @measure_time decorator."""

    def test_sync_function(self):
        """Test decorator on synchronous function."""
        @measure_time
        def slow_function():
            time.sleep(0.1)
            return "done"
        
        result = slow_function()
        
        assert result == "done"

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test decorator on async function."""
        import asyncio
        
        @measure_time
        async def async_slow_function():
            await asyncio.sleep(0.1)
            return "async done"
        
        result = await async_slow_function()
        
        assert result == "async done"

    def test_function_with_args(self):
        """Test decorator preserves function arguments."""
        @measure_time
        def add(a, b):
            return a + b
        
        result = add(2, 3)
        
        assert result == 5

    def test_function_with_kwargs(self):
        """Test decorator preserves keyword arguments."""
        @measure_time
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"
        
        result = greet("World", greeting="Hi")
        
        assert result == "Hi, World!"

    def test_preserves_function_name(self):
        """Test decorator preserves function metadata."""
        @measure_time
        def my_function():
            """My docstring."""
            pass
        
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestConfig:
    """Test suite for configuration."""

    def test_settings_from_env(self):
        """Test Settings loads from environment."""
        # Settings are loaded at app startup from environment
        settings = get_settings()
        
        # Verify we have a database URL (from env or default)
        assert settings.database_url is not None
        assert len(settings.database_url) > 0

    def test_settings_defaults(self):
        """Test Settings has sensible defaults."""
        settings = get_settings()
        
        # Verify defaults are set
        assert settings.aws_region == "us-east-1"
        assert settings.app_name == "Maintenance Service API"

    def test_debug_parsing(self):
        """Test that debug setting is loaded."""
        settings = get_settings()
        # Should be boolean
        assert isinstance(settings.debug, bool)

    def test_settings_caching(self):
        """Test get_settings returns cached instance."""
        get_settings.cache_clear()
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test /health endpoint returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        # Root endpoint returns app metadata
        assert "name" in data or "version" in data or "docs_url" in data
