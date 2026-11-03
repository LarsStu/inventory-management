"""
Tests for restocking order API endpoints.
"""
import pytest
import mock_data


@pytest.fixture(autouse=True)
def clear_restocking_orders():
    """Restocking orders live in shared module state, so reset them around each test."""
    mock_data.restocking_orders.clear()
    yield
    mock_data.restocking_orders.clear()


class TestRestockingEndpoints:
    """Test suite for restocking order endpoints."""

    def test_create_restocking_order_success(self, client):
        """Test submitting a valid restocking order returns 201 with computed totals."""
        payload = {
            "budget": 5000,
            "items": [
                {"sku": "WDG-001", "quantity": 10},   # 42.50 each
                {"sku": "GSK-203", "quantity": 100},  # 6.20 each
            ],
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        assert order["total_value"] == pytest.approx(1045.00)
        assert len(order["items"]) == 2

    def test_restocking_order_prices_come_from_server(self, client):
        """Test unit cost is taken from the forecast catalog, not the request body."""
        payload = {
            "budget": 5000,
            "items": [{"sku": "WDG-001", "quantity": 2}],
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201

        line = response.json()["items"][0]
        assert line["unit_cost"] == pytest.approx(42.50)
        assert line["line_total"] == pytest.approx(85.00)

    def test_restocking_order_lead_time_is_longest_item(self, client):
        """Test order lead time equals the slowest item, not the sum of lead times."""
        # WDG-001 has a 7-day lead time and GSK-203 has 4 days
        payload = {
            "budget": 5000,
            "items": [
                {"sku": "WDG-001", "quantity": 1},
                {"sku": "GSK-203", "quantity": 1},
            ],
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["lead_time_days"] == 7
        assert order["expected_delivery"] > order["submitted_date"]

    def test_created_order_appears_in_list(self, client):
        """Test a submitted order is returned by the list endpoint."""
        payload = {"budget": 1000, "items": [{"sku": "GSK-203", "quantity": 10}]}
        created = client.post("/api/restocking-orders", json=payload).json()

        response = client.get("/api/restocking-orders")
        assert response.status_code == 200

        ids = [order["id"] for order in response.json()]
        assert created["id"] in ids

    def test_list_restocking_orders_newest_first(self, client):
        """Test restocking orders are sorted with the most recent submission first."""
        for sku in ["GSK-203", "WDG-001"]:
            client.post("/api/restocking-orders", json={"budget": 1000, "items": [{"sku": sku, "quantity": 1}]})

        orders = client.get("/api/restocking-orders").json()
        dates = [order["submitted_date"] for order in orders]
        assert dates == sorted(dates, reverse=True)

    def test_restocking_order_over_budget_rejected(self, client):
        """Test an order whose total exceeds the budget returns 400."""
        payload = {"budget": 100, "items": [{"sku": "WDG-001", "quantity": 10}]}  # 425.00
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()

    def test_restocking_order_unknown_sku_rejected(self, client):
        """Test an unknown SKU returns 400."""
        payload = {"budget": 1000, "items": [{"sku": "NOT-REAL", "quantity": 1}]}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 400
        assert "NOT-REAL" in response.json()["detail"]

    def test_restocking_order_empty_items_rejected(self, client):
        """Test an order with no items returns 400."""
        response = client.post("/api/restocking-orders", json={"budget": 1000, "items": []})
        assert response.status_code == 400

    def test_restocking_order_non_positive_quantity_rejected(self, client):
        """Test a zero or negative quantity returns 400."""
        for quantity in [0, -5]:
            payload = {"budget": 1000, "items": [{"sku": "GSK-203", "quantity": quantity}]}
            response = client.post("/api/restocking-orders", json=payload)
            assert response.status_code == 400

    def test_restocking_order_duplicate_sku_rejected(self, client):
        """Test the same SKU listed twice returns 400."""
        payload = {
            "budget": 1000,
            "items": [
                {"sku": "GSK-203", "quantity": 1},
                {"sku": "GSK-203", "quantity": 2},
            ],
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 400

    def test_rejected_order_is_not_stored(self, client):
        """Test a rejected order does not appear in the list."""
        client.post("/api/restocking-orders", json={"budget": 1, "items": [{"sku": "WDG-001", "quantity": 10}]})
        assert client.get("/api/restocking-orders").json() == []

    def test_regular_orders_unaffected_by_restocking(self, client):
        """Test submitting restocking orders does not change the regular orders list."""
        before = client.get("/api/orders").json()
        client.post("/api/restocking-orders", json={"budget": 1000, "items": [{"sku": "GSK-203", "quantity": 1}]})
        after = client.get("/api/orders").json()
        assert len(after) == len(before)

    def test_demand_forecast_exposes_restocking_fields(self, client):
        """Test demand forecasts include the cost and lead time used for restocking."""
        response = client.get("/api/demand")
        assert response.status_code == 200

        for forecast in response.json():
            assert isinstance(forecast["unit_cost"], (int, float))
            assert isinstance(forecast["supplier"], str)
            assert isinstance(forecast["lead_time_days"], int)
