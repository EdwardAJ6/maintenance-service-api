"""
Tests for Categories endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status


class TestCategories:
    """Test suite for /categories endpoints."""

    def test_create_category_success(self, client: TestClient, sample_category: dict):
        """Test creating a category returns 201."""
        response = client.post("/categories/", json=sample_category, headers=client.headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == sample_category["name"]
        assert data["description"] == sample_category["description"]
        assert "id" in data
        assert "created_at" in data

    def test_create_category_duplicate_name(self, client: TestClient, sample_category: dict):
        """Test creating duplicate category returns 409."""
        client.post("/categories/", json=sample_category, headers=client.headers)
        response = client.post("/categories/", json=sample_category, headers=client.headers)
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_create_category_missing_name(self, client: TestClient):
        """Test creating category without name returns 422."""
        response = client.post("/categories/", json={"description": "Test"}, headers=client.headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_categories_empty(self, client: TestClient):
        """Test listing categories when empty."""
        response = client.get("/categories/", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_categories(self, client: TestClient, sample_category: dict):
        """Test listing categories returns all."""
        client.post("/categories/", json=sample_category, headers=client.headers)
        client.post("/categories/", json={"name": "Mecánica", "description": "Repuestos mecánicos"}, headers=client.headers)
        
        response = client.get("/categories/", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

    def test_list_categories_pagination(self, client: TestClient):
        """Test categories pagination."""
        for i in range(5):
            client.post("/categories/", json={"name": f"Category {i}"}, headers=client.headers)
        
        response = client.get("/categories/?skip=2&limit=2", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_get_category_by_id(self, client: TestClient, sample_category: dict):
        """Test getting category by ID."""
        create_response = client.post("/categories/", json=sample_category, headers=client.headers)
        category_id = create_response.json()["id"]
        
        response = client.get(f"/categories/{category_id}", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == sample_category["name"]

    def test_get_category_not_found(self, client: TestClient):
        """Test getting non-existent category returns 404."""
        response = client.get("/categories/999", headers=client.headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_category(self, client: TestClient, sample_category: dict):
        """Test deleting a category."""
        create_response = client.post("/categories/", json=sample_category, headers=client.headers)
        category_id = create_response.json()["id"]
        
        response = client.delete(f"/categories/{category_id}", headers=client.headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deleted
        get_response = client.get(f"/categories/{category_id}", headers=client.headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_category_not_found(self, client: TestClient):
        """Test deleting non-existent category returns 404."""
        response = client.delete("/categories/999", headers=client.headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
