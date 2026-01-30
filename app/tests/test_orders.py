"""
Tests for Orders endpoints including idempotency.
Orders link items (spare parts) with TechnicalReport entities.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status


class TestOrders:
    """Test suite for /orders endpoints."""

    def _create_item(self, client: TestClient, sku: str = "TST-001") -> int:
        """Helper to create an item for orders."""
        response = client.post("/items/", json={
            "name": "Test Item",
            "sku": sku,
            "price": 50.00,
            "stock": 100
        }, headers=client.headers)
        return response.json()["id"]
    
    def _build_order_data(self, request_id: str, item_id: int, quantity: int = 2) -> dict:
        """Helper to build order data with TechnicalReport."""
        return {
            "request_id": request_id,
            "technical_report": {
                "title": "Mantenimiento preventivo",
                "description": "Revisión general del equipo",
                "diagnosis": "Desgaste normal en componentes",
                "recommendations": "Programar siguiente revisión en 3 meses"
            },
            "items": [{"item_id": item_id, "quantity": quantity}]
        }

    def test_create_order_success(self, client: TestClient):
        """Test creating an order returns 201 and links items with technical report."""
        item_id = self._create_item(client)
        
        order_data = self._build_order_data("ORD-001", item_id, quantity=2)
        response = client.post("/orders/", json=order_data, headers=client.headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["request_id"] == "ORD-001"
        assert data["status"] == "pending"
        
        # Verify technical report is linked
        assert "technical_report" in data
        assert data["technical_report"]["title"] == "Mantenimiento preventivo"
        assert data["technical_report"]["diagnosis"] == "Desgaste normal en componentes"
        
        # Verify items are linked
        assert len(data["items"]) == 1
        assert float(data["total_amount"]) == 100.00

    def test_create_order_idempotency(self, client: TestClient):
        """Test order creation is idempotent (same request_id returns existing)."""
        item_id = self._create_item(client, sku="IDEM-001")
        order_data = self._build_order_data("ORD-IDEM-001", item_id, quantity=1)
        
        # First request - creates order
        response1 = client.post("/orders/", json=order_data, headers=client.headers)
        assert response1.status_code == status.HTTP_201_CREATED
        order_id = response1.json()["id"]
        
        # Second request with same request_id - returns existing
        response2 = client.post("/orders/", json=order_data, headers=client.headers)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["id"] == order_id

    def test_create_order_stock_decreases(self, client: TestClient):
        """Test that creating an order decreases item stock."""
        item_id = self._create_item(client, sku="STOCK-001")
        initial_stock = 100
        order_quantity = 10
        
        order_data = self._build_order_data("ORD-STOCK-001", item_id, quantity=order_quantity)
        client.post("/orders/", json=order_data, headers=client.headers)
        
        item_response = client.get(f"/items/{item_id}", headers=client.headers)
        assert item_response.json()["stock"] == initial_stock - order_quantity

    def test_create_order_insufficient_stock(self, client: TestClient):
        """Test creating order with insufficient stock returns 400."""
        item_id = self._create_item(client, sku="NOSTOCK-001")
        
        response = client.post("/orders/", json={
            "request_id": "ORD-NOSTOCK-001",
            "technical_report": {
                "title": "Test insufficient stock",
                "description": "Should fail due to stock"
            },
            "items": [{"item_id": item_id, "quantity": 999}]
        }, headers=client.headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient stock" in response.json()["detail"]

    def test_create_order_item_not_found(self, client: TestClient):
        """Test creating order with non-existent item returns 400."""
        response = client.post("/orders/", json={
            "request_id": "ORD-NOTFOUND-001",
            "technical_report": {
                "title": "Test not found",
                "description": "Item does not exist"
            },
            "items": [{"item_id": 999, "quantity": 1}]
        }, headers=client.headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_order_empty_items(self, client: TestClient):
        """Test creating order without items returns 422."""
        response = client.post("/orders/", json={
            "request_id": "ORD-EMPTY-001",
            "technical_report": {
                "title": "Test empty",
                "description": "No items"
            },
            "items": []
        }, headers=client.headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_order_multiple_items(self, client: TestClient):
        """Test creating order with multiple items linked to one technical report."""
        # Create two items
        response1 = client.post("/items/", json={
            "name": "Item 1", "sku": "MULTI-001", "price": 10.00, "stock": 50
        }, headers=client.headers)
        response2 = client.post("/items/", json={
            "name": "Item 2", "sku": "MULTI-002", "price": 20.00, "stock": 50
        }, headers=client.headers)
        item1_id = response1.json()["id"]
        item2_id = response2.json()["id"]
        
        response = client.post("/orders/", json={
            "request_id": "ORD-MULTI-001",
            "technical_report": {
                "title": "Multiple items maintenance",
                "description": "Replacing multiple parts",
                "diagnosis": "Multiple components worn",
                "recommendations": "Check again in 6 months"
            },
            "items": [
                {"item_id": item1_id, "quantity": 2},  # 20.00
                {"item_id": item2_id, "quantity": 3}   # 60.00
            ]
        }, headers=client.headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["items"]) == 2
        assert float(data["total_amount"]) == 80.00
        # Verify both items are linked to the same technical report
        assert data["technical_report"]["title"] == "Multiple items maintenance"

    def test_list_orders_empty(self, client: TestClient):
        """Test listing orders when empty."""
        response = client.get("/orders/", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_orders(self, client: TestClient):
        """Test listing orders with their linked technical reports."""
        item_id = self._create_item(client, sku="LIST-001")
        
        # Create two orders
        order1 = self._build_order_data("ORD-LIST-001", item_id, quantity=1)
        order1["technical_report"]["title"] = "Order 1 Report"
        client.post("/orders/", json=order1, headers=client.headers)
        
        order2 = self._build_order_data("ORD-LIST-002", item_id, quantity=1)
        order2["technical_report"]["title"] = "Order 2 Report"
        client.post("/orders/", json=order2, headers=client.headers)
        
        response = client.get("/orders/", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_get_order_by_id(self, client: TestClient):
        """Test getting order by ID with its linked technical report."""
        item_id = self._create_item(client, sku="GETID-001")
        
        order_data = self._build_order_data("ORD-GET-001", item_id)
        order_data["technical_report"]["title"] = "Specific Report"
        create_response = client.post("/orders/", json=order_data, headers=client.headers)
        order_id = create_response.json()["id"]
        
        response = client.get(f"/orders/{order_id}", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["request_id"] == "ORD-GET-001"
        assert response.json()["technical_report"]["title"] == "Specific Report"

    def test_get_order_not_found(self, client: TestClient):
        """Test getting non-existent order returns 404."""
        response = client.get("/orders/999", headers=client.headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_order_by_request_id(self, client: TestClient):
        """Test getting order by request_id."""
        item_id = self._create_item(client, sku="REQID-001")
        request_id = "ORD-REQID-001"
        
        order_data = self._build_order_data(request_id, item_id)
        client.post("/orders/", json=order_data, headers=client.headers)
        
        response = client.get(f"/orders/request/{request_id}", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["request_id"] == request_id

    def test_get_order_by_request_id_not_found(self, client: TestClient):
        """Test getting order by non-existent request_id returns 404."""
        response = client.get("/orders/request/NONEXISTENT", headers=client.headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_order_status(self, client: TestClient):
        """Test updating order status."""
        item_id = self._create_item(client, sku="STATUS-001")
        
        order_data = self._build_order_data("ORD-STATUS-001", item_id)
        create_response = client.post("/orders/", json=order_data, headers=client.headers)
        order_id = create_response.json()["id"]
        
        response = client.patch(f"/orders/{order_id}/status?new_status=in_progress", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "in_progress"

    def test_update_order_status_completed(self, client: TestClient):
        """Test marking order as completed."""
        item_id = self._create_item(client, sku="COMPLETE-001")
        
        order_data = self._build_order_data("ORD-COMPLETE-001", item_id)
        create_response = client.post("/orders/", json=order_data, headers=client.headers)
        order_id = create_response.json()["id"]
        
        # First move to in_progress
        client.patch(f"/orders/{order_id}/status?new_status=in_progress", headers=client.headers)
        
        # Then complete
        response = client.patch(f"/orders/{order_id}/status?new_status=completed", headers=client.headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "completed"

    def test_update_order_status_cancelled_restores_stock(self, client: TestClient):
        """Test cancelling order restores item stock."""
        item_id = self._create_item(client, sku="CANCEL-001")
        initial_stock = 100
        order_quantity = 10
        
        order_data = self._build_order_data("ORD-CANCEL-001", item_id, quantity=order_quantity)
        create_response = client.post("/orders/", json=order_data, headers=client.headers)
        order_id = create_response.json()["id"]
        
        # Verify stock decreased
        item_response = client.get(f"/items/{item_id}", headers=client.headers)
        assert item_response.json()["stock"] == initial_stock - order_quantity
        
        # Cancel order
        client.patch(f"/orders/{order_id}/status?new_status=cancelled", headers=client.headers)
        
        # Verify stock restored
        item_response = client.get(f"/items/{item_id}", headers=client.headers)
        assert item_response.json()["stock"] == initial_stock

    def test_cannot_change_cancelled_order(self, client: TestClient):
        """Test that cancelled orders cannot be modified."""
        item_id = self._create_item(client, sku="CANTCHANGE-001")
        
        order_data = self._build_order_data("ORD-CANTCHANGE-001", item_id)
        create_response = client.post("/orders/", json=order_data, headers=client.headers)
        order_id = create_response.json()["id"]
        
        # Cancel order
        client.patch(f"/orders/{order_id}/status?new_status=cancelled", headers=client.headers)
        
        # Try to change status
        response = client.patch(f"/orders/{order_id}/status?new_status=in_progress", headers=client.headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_change_completed_order(self, client: TestClient):
        """Test that completed orders cannot be changed."""
        item_id = self._create_item(client, sku="COMPLETED-001")
        
        order_data = self._build_order_data("ORD-COMPLETED-001", item_id)
        create_response = client.post("/orders/", json=order_data, headers=client.headers)
        order_id = create_response.json()["id"]
        
        # Move to in_progress then complete
        client.patch(f"/orders/{order_id}/status?new_status=in_progress", headers=client.headers)
        client.patch(f"/orders/{order_id}/status?new_status=completed", headers=client.headers)
        
        # Try to change status back
        response = client.patch(f"/orders/{order_id}/status?new_status=pending", headers=client.headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_technical_report_fields_optional(self, client: TestClient):
        """Test that diagnosis and recommendations are optional in technical report."""
        item_id = self._create_item(client, sku="OPTIONAL-001")
        
        response = client.post("/orders/", json={
            "request_id": "ORD-OPTIONAL-001",
            "technical_report": {
                "title": "Minimal Report",
                "description": "Only required fields"
                # diagnosis and recommendations are optional
            },
            "items": [{"item_id": item_id, "quantity": 1}]
        }, headers=client.headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["technical_report"]["title"] == "Minimal Report"
        assert data["technical_report"]["diagnosis"] is None
        assert data["technical_report"]["recommendations"] is None