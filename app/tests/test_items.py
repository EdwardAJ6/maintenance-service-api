"""
Tests for Items endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status


class TestItems:
    """Test suite for /items endpoints."""

    def test_create_item_success(self, client: TestClient, sample_item: dict):
        """Test creating an item returns 201."""
        response = client.post("/items/", json=sample_item, headers=client.headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == sample_item["name"]
        assert data["sku"] == sample_item["sku"]
        assert float(data["price"]) == sample_item["price"]
        assert data["stock"] == sample_item["stock"]
        assert "id" in data

    def test_create_item_with_category(self, client: TestClient, sample_item: dict, sample_category: dict):
        """Test creating item with category."""
        cat_response = client.post("/categories/", json=sample_category, headers=client.headers)
        category_id = cat_response.json()["id"]
        
        sample_item["category_id"] = category_id
        response = client.post("/items/", json=sample_item, headers=client.headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["category_id"] == category_id
        assert data["category"]["name"] == sample_category["name"]

    def test_create_item_duplicate_sku(self, client: TestClient, sample_item: dict):
        """Test creating item with duplicate SKU returns 409."""
        client.post("/items/", json=sample_item, headers=client.headers)
        response = client.post("/items/", json=sample_item, headers=client.headers)
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_create_item_invalid_category(self, client: TestClient, sample_item: dict):
        """Test creating item with non-existent category returns 400."""
        sample_item["category_id"] = 999
        response = client.post("/items/", json=sample_item, headers=client.headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_item_invalid_price(self, client: TestClient):
        """Test creating item with negative price returns 422."""
        response = client.post("/items/", json={
            "name": "Test",
            "sku": "TST-001",
            "price": -10,
            "stock": 10
        }, headers=client.headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_item_invalid_stock(self, client: TestClient):
        """Test creating item with negative stock returns 422."""
        response = client.post("/items/", json={
            "name": "Test",
            "sku": "TST-001",
            "price": 10,
            "stock": -5
        }, headers=client.headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_items_empty(self, client: TestClient):
        """Test listing items when empty."""
        response = client.get("/items/", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_items(self, client: TestClient, sample_item: dict):
        """Test listing items."""
        client.post("/items/", json=sample_item, headers=client.headers)
        client.post("/items/", json={**sample_item, "sku": "FIL-ACE-002", "name": "Filtro de Aire"}, headers=client.headers)
        
        response = client.get("/items/", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_list_items_with_category_filter(self, client: TestClient, sample_item: dict, sample_category: dict):
        """Test filtering items by category."""
        cat_response = client.post("/categories/", json=sample_category, headers=client.headers)
        category_id = cat_response.json()["id"]
        
        client.post("/items/", json={**sample_item, "category_id": category_id}, headers=client.headers)
        client.post("/items/", json={**sample_item, "sku": "FIL-002", "name": "Item sin categoría"}, headers=client.headers)
        
        response = client.get(f"/items/?category_id={category_id}", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    def test_list_items_with_sku_filter(self, client: TestClient, sample_item: dict):
        """Test filtering items by SKU (B-Tree index)."""
        client.post("/items/", json=sample_item, headers=client.headers)
        
        response = client.get(f"/items/?sku={sample_item['sku']}", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["sku"] == sample_item["sku"]

    def test_get_item_by_id(self, client: TestClient, sample_item: dict):
        """Test getting item by ID."""
        create_response = client.post("/items/", json=sample_item, headers=client.headers)
        item_id = create_response.json()["id"]
        
        response = client.get(f"/items/{item_id}", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["sku"] == sample_item["sku"]

    def test_get_item_not_found(self, client: TestClient):
        """Test getting non-existent item returns 404."""
        response = client.get("/items/999", headers=client.headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_item_stock(self, client: TestClient, sample_item: dict):
        """Test partial update of item stock (PATCH)."""
        create_response = client.post("/items/", json=sample_item, headers=client.headers)
        item_id = create_response.json()["id"]
        
        response = client.patch(f"/items/{item_id}", json={"stock": 200}, headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["stock"] == 200
        assert response.json()["price"] == str(sample_item["price"])  # Unchanged

    def test_patch_item_price(self, client: TestClient, sample_item: dict):
        """Test partial update of item price (PATCH)."""
        create_response = client.post("/items/", json=sample_item, headers=client.headers)
        item_id = create_response.json()["id"]
        
        response = client.patch(f"/items/{item_id}", json={"price": 35.99}, headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert float(response.json()["price"]) == 35.99
        assert response.json()["stock"] == sample_item["stock"]  # Unchanged

    def test_patch_item_multiple_fields(self, client: TestClient, sample_item: dict):
        """Test updating multiple fields."""
        create_response = client.post("/items/", json=sample_item, headers=client.headers)
        item_id = create_response.json()["id"]
        
        response = client.patch(f"/items/{item_id}", json={
            "stock": 50,
            "price": 19.99,
            "name": "Nuevo Nombre"
        }, headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["stock"] == 50
        assert float(data["price"]) == 19.99
        assert data["name"] == "Nuevo Nombre"

    def test_patch_item_not_found(self, client: TestClient):
        """Test patching non-existent item returns 404."""
        response = client.patch("/items/999", json={"stock": 10}, headers=client.headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_item(self, client: TestClient, sample_item: dict):
        """Test deleting an item."""
        create_response = client.post("/items/", json=sample_item, headers=client.headers)
        item_id = create_response.json()["id"]
        
        response = client.delete(f"/items/{item_id}", headers=client.headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_item_not_found(self, client: TestClient):
        """Test deleting non-existent item returns 404."""
        response = client.delete("/items/999", headers=client.headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_by_sku(self, client: TestClient, sample_item: dict):
        """Test searching item by SKU."""
        client.post("/items/", json=sample_item, headers=client.headers)
        
        response = client.get(f"/items/search/sku/{sample_item['sku']}", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["sku"] == sample_item["sku"]

    def test_search_by_sku_not_found(self, client: TestClient):
        """Test searching non-existent SKU returns 404."""
        response = client.get("/items/search/sku/NONEXISTENT")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
